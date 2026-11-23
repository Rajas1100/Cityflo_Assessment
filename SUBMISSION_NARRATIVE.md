# Is route X running late right now, and by how much?

*Submission narrative for Staff Engineers, Data Engineers and Operations Leads. Decisions and their defence are in `DECISION_RECORD.md`.*

> **Evidence base.** The real Cityflo bundle: 6 routes, 19 trips, 4,465 pings (4,464 parseable), 201 bookings, mornings of
> 15 to 17 June 2026, as-of 07:45 on the 17th. A separate synthetic bundle (`cityflo_dummy_data/`) was built earlier and is used
> **only as a test harness** for edge cases; no finding below comes from it.

---

## 1. Business understanding

Priya needs one row per route before 07:45: late or not, by how much, and which of three actions (push to riders, hold a
connection, call the driver). Her constraint decides the design: **a confidently wrong "late" number is worse than no number**,
and "I don't know, here's why" is a valid line. So the product is a decision with evidence, and a blank is a first-class answer.

`HANDOFF.md` also carries two "reconciliation rules": drop operator 7's vehicles, and report Route 12 as on-time. Both conflict
with that constraint, so neither was applied (D3 and D6 in the record).

## 2. Definition of lateness

**Delay = when the bus was at its position − when the timetable says it should be there.** Late at ≥ 3 min, early at ≤ −3 min.
Three rules make it safe: a standing bus gets later by the second; a bus still at its origin is late by time past departure;
missing or stale data is never read as on time.

Why the timetable: `promised_eta` equals the linear-by-distance timetable on 189 of 201 bookings, and the 12 completed
history trips all finished within −1.7 to +2.3 min of it, so a 3 min line separates normal from abnormal. The 12 exceptions are
the defect found in Section 6.

## 3. Data model

Three layers: **raw** pings as received, **enriched** (trip, distance along route, quality flags), **results** (snapshot,
delay, verdict). Key choices: both clocks kept (`recorded_at` for where and when, `received_at` for what was knowable); stops keyed
by `(route_id, seq)`; vehicle-to-trip assignment explicit; flags instead of deletes. The MVP computes the enriched and result
layers in memory per query (about 0.1 s) rather than persisting them. Schemas: `docs/design_notes.md`.

## 4. Computation approach

One pass per query, keyed on an as-of time: (1) filter to `received_at ≤ as-of`, parse `+05:30` stamps, quarantine unparseable
rows, de-duplicate by content; (2) clock check, excluding (not re-timing) any vehicle offset by more than 15 min; (3) stops →
polyline → cumulative distance; (4) trip assignment; (5) reject out-of-area, off-route and speed-spike pings, snap to distance
along route, keep progress monotone; (6) delay at the last trustworthy ping; (7) trust gates and confidence; (8) a verdict in
the assignment's vocabulary with precedence **CALL_DRIVER > PUSH_LATE > NO_VERDICT > HOLD**; (9) a plain-language dashboard
card under 90 words.

## 5. Validation strategy

| Check | Result |
|---|---|
| Hand-verify every live Wednesday trip against raw pings | All six verdicts reproduced by reading the rows |
| Normal mornings: engine every 10 min on Mon and Tue, all routes | 131 HOLD, 1 NO_VERDICT of 132; 0 false pushes, 0 false calls |
| Leakage: only `received_at ≤ 07:45` is used | V-04 shows 52 of 197 pings known, as it should |
| 14 synthetic scenario fixtures (gaps, duplicates, out-of-order, stoppage, hold, diversion...) | 14/14 pass; the first run found 3 defects in the engine |
| 9 synthetic false-late probes | 8 of 9 still labelled late (Section 8) |
| 50 dashboard cards, 6 checks | All pass, 39 to 90 words |

The engine's **first real-data run was confidently wrong**: it called Route 11 "late 59.0 min, 0.95 confidence". Reading the
raw pings showed the bus never left the origin. That became the `NOT_DEPARTED` rule and the CALL_DRIVER verdict.

## 6. Key findings from the data

**Observations**

| Route | Verdict | Evidence |
|---|---|---|
| 11 | CALL_DRIVER | V-06: 192 pings within 14 m of the origin, ≤ 2.7 km/h, 59 min after departure, GPS 9 s old |
| 17 | NO_VERDICT | V-05 ran up to 9 min early, stopped at the Dadar TT stop at 14.57 km, silent since 07:27:40 |
| 12 | PUSH_LATE 10 min | V-10 first ping 07:15:00 at the origin vs 07:05; delay 9.9 to 10.1 over 5.7 km; history +1.6, +2.3 |
| 14 | NO_VERDICT | V-04: 52 of 197 pings known; 145 pings carry an exact 5,400 s received-minus-recorded offset |
| 21 | HOLD | V-03 −0.3 min, V-09 (operator 7) +1.0 min, both with fresh GPS |
| 9 | HOLD | V-11 reached its last stop at 07:44:42, +0.4 min |

Worry-order: **11, 17, 12, 14, 21, 9.**

**Data defects**
- 12 corrupt promised ETAs, all on Wednesday (TRIP_017: 6 of 16, 9.0 to 37.8 min early; TRIP_018: 6 of 6, exactly 19.0 min early, 4 earlier than the trip's own start). Monday and Tuesday: 0 of 132.
- 41 of 201 bookings board at their route's last stop, so "riders ahead" counts are inflated.
- 1 unparseable timestamp (`06:60:23`), 1 `ping_id` collision plus replay, 3 teleport pings (6,500 to 7,800 km/h), 1 negative speed.

**Interpretation** (hypotheses, not facts): V-04's constant 90 min offset looks like an ingest-clock fault, not a transmission
delay; on its own device clock the bus was −0.0 to +0.7 min all trip, so it was probably fine. V-05's pause at a stop while
running early is consistent with a timing-point hold, a dead device, or a breakdown; the data cannot separate them.

## 7. Cases that looked late but were not (and the reverse)

- **Route 11, "59 min late".** Not a lateness: the bus isn't running. A push would send a meaningless number to 8 bookings.
- **Route 14, looks stalled.** The bus was on time on its device clock; only the delivery stamp was wrong.
- **Route 21, TRIP_018.** Late by 19 min against its promised ETAs, on time (−0.3) against the timetable. The promises are the defect.
- **Route 9, three impossible pings.** Teleports at 6,500+ km/h would show a bus kilometres off route; rejected.
- **Looked fine but isn't.** Route 11's GPS is fresh and cadence normal, so a feed-health check says "healthy" while the bus sits still.
- **My own clock rule.** Re-timing V-04 by arrival would have read it 90 min late once its later pings arrived; replaced with exclusion.
- **Route 12 is the reverse case:** it looks suspicious only because a rule says to zero it. The measurement is solid.

## 8. Limitations

- Linear timetable and straight-line geometry; fine on this data (history within ±2.3 min) but only 12 trips support it.
- The 10 min "not departed" rule was written after seeing Wednesday; history shows it causes no false alarms, not that 10 is right.
- 8 of 9 synthetic false-late probes still produce a late label (transient queue, drift, planned halt, stale schedule); none occurs on the real normal mornings.
- No forecast of arrival at a rider's stop; confidence is a heuristic, not a probability.
- Which clock to trust for V-04 is unresolved; the verdict is conservative on purpose.
- Built with an AI assistant; the author's own steering decisions are documented separately in `decisions.jsonl`.

## 9. Future improvements

1. Ingest-log check on V-04's 06:57 offset; alert on any vehicle offset above 15 min.
2. Correct promised ETAs for TRIP_017 and TRIP_018 and add a promise-vs-timetable validator at booking time.
3. Persistence and trend rules so transient delays do not become pushes.
4. Treat standing near the last stop as arrival; reject last-stop boardings at ingestion.
5. Calibrate thresholds and confidence by backtesting mid-trip estimates against final arrival once more history exists.
6. Real stop-level timetable and learned segment speeds if congestion shows up in more data.
7. Persist the enriched and result tables, log every verdict with its inputs for audit.

---
*Reproduce:* `python run_0745.py && python real_data_analysis.py && python history_false_alarm_check.py` (real data in `./data`).
