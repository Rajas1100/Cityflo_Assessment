# Decision record: 07:45 on Wednesday 2026-06-17

For Priya. All numbers come from the real bundle via `real_data_analysis.py` and `run_0745.py`; outputs are in `results_real/`.
Only pings with `received_at ≤ 07:45` count as known. The ±3 min and 8 min thresholds were set before I looked at Wednesday, and Monday and Tuesday support them: all 12 completed
trips finished between −1.7 and +2.3 min of the timetable. **The 10 min "not departed" rule was written after I saw V-06 on
Wednesday**; history can only show it causes no false alarms (see D8), not that 10 is the right number.

## The wall

| Route | Verdict | One-line reason |
|---|---|---|
| 11 Borivali → BKC | **CALL_DRIVER** | TRIP_014 / V-06 has not left Borivali Stn: 59 min past its 06:46 departure, 192 pings within 14 m of the origin, max 2.7 km/h, GPS 9 s old. |
| 17 Vashi → Worli | **NO_VERDICT** | TRIP_017 / V-05 silent since 07:27:40 (17 min), stopped at the Dadar TT stop after running up to 9 min early. |
| 12 Mulund → Andheri E | **PUSH_LATE 10 min** | TRIP_015 / V-10 left the origin at 07:15 for a 07:05 departure; delay is a flat 9.9 to 10.1 min over 5.7 km; GPS 9 s old. |
| 14 Kandivali → Lower Parel | **NO_VERDICT** | TRIP_016 / V-04: the server holds 52 of 197 pings, the last 48 min old; 145 later pings carry an exact 5,400 s received-minus-recorded offset. |
| 21 Ghatkopar → BKC | **HOLD** | TRIP_018 (−0.3 min) and TRIP_019 (+1.0 min, operator 7) are on the timetable; separately, TRIP_018's riders were shown ETAs 19.0 min early. |
| 9 Thane → Powai | **HOLD** | TRIP_013 reached its last stop at 07:44:42, +0.4 min. |

**Worry-order: 11, 17, 12, 14, 21, 9.**
1. **Route 11.** The facts are certain, the problem grows one minute per minute, and only a phone call fixes it. Of 8 bookings, 5 board at real stops (3 board at the destination, a data defect), and 4 of those 5 already have a promised ETA in the past.
2. **Route 17.** The highest uncertainty with real exposure: one call resolves it, and every rider ahead of this bus (6 bookings, 3 valid) holds a promised ETA that has already passed.
3. **Route 12.** Decided, and the push can go now. It ranks third because it needs seconds, not chasing, but expect it to be challenged (see D3).
4. **Route 14.** Most likely fine (see D4); a one-line check with the data team.
5. **Route 21.** On time, but the promise defect needs fixing.
6. **Route 9.** Done.

## Calls

### D1. "Late" = delay against the timetable at the bus's current position
- **Rule.** Delay = the time the bus was at its snapped position along the route minus the time the linear-by-distance timetable puts it there (`start + runtime × distance / length`). Late at ≥ 3 min, early at ≤ −3 min. If the bus is standing, the time since its last ping is added. At the origin, delay = now minus scheduled departure.
- **Why this one.** The in-app `promised_eta` equals this timetable exactly on 189 of 201 bookings (all 132 on Monday and Tuesday). Monday and Tuesday show no mid-route congestion bulge: delay at 50% of the route ranged −0.8 to +1.2 min, so a straight-line timetable is adequate here.
- **Where it breaks.** TRIP_018: all 6 bookings have a promised ETA exactly 19.0 min earlier than the timetable, and 4 of them (BKG_0190, 0192, 0193, 0195) are earlier than the trip's own 07:20 start. Measured against the promise, TRIP_018 would read PUSH_LATE 19 while the bus is at −0.3. I keep the timetable.
- **Cost, and who eats it.** If the promise is right and the timetable wrong, 6 bookings (1 valid rider still ahead) get no push; the depot hears about it from riders. If I used the promise, I'd push a 19 min "late" built from a number I can show is corrupt, which is the wrongly-confident push Priya described.
- **What would flip it.** Priya or the app team confirm TRIP_018's earlier ETAs reflect a real revised schedule.

### D2. Route 11 is CALL_DRIVER, not "PUSH_LATE 59"
- **Rule.** GPS ≤ 3 min old, still within 300 m of the origin, ≥ 10 min after scheduled departure → CALL_DRIVER. A push says "n minutes late", which assumes the bus is coming.
- **Where it breaks.** It would also fire on a bus held at the depot by dispatch; the call is still right. At the departure minute only 1 to 2 pings exist, so on Monday 06:40 the engine returned NO_VERDICT for Route 11, not a false alarm (see D8).
- **Cost.** False push: 8 booked riders get a number with no meaning. Suppressed: 4 riders whose promised ETA already passed are left unannounced. A needless call costs the depot one conversation. The GPS shows jitter, not a frozen unit: 9 distinct positions in 192 pings, max 14 m from the origin.
- **What would flip it.** Any ping more than 300 m from the origin, or the driver stating a later authorised departure; then PUSH_LATE with n = now minus that departure.

### D3. Route 12 is PUSH_LATE 10 min, and I did not apply the "report as on-time" rule
- **Rule.** Trusted data (GPS ≤ 3 min old, ≥ 8 pings in 10 min), position-based delay ≥ 3 min, confidence ≥ 0.6 → PUSH_LATE round(delay).
- **Evidence.** V-10's first ping is 07:15:00 at the origin (km 0.00) against a 07:05 departure. On Monday and Tuesday every first ping was exactly at the scheduled start. Across 91 pings the delay stays between 9.9 and 10.1: it left late and neither recovered nor slipped. Route 12's history arrival delay was +2.3 and +1.6.
- **The HANDOFF rule.** `HANDOFF.md` rev. C says to report Route 12 as on-time (lateness = 0). I did not apply it. It replaces a measured +10.0 min with zero, which contradicts Priya's own instruction that a wrong number is worse than none. I show the measured number and flag the conflict.
- **Where it breaks.** The 07:05 to 07:15 gap has no pings, so I can't tell whether the bus idled at the origin or the device was off; either way the bus was at the origin at 07:15. The delay is flat, so recovery or slippage over the last 5.7 km could move it by about ±1 min by the time riders see it.
- **Cost.** 9 bookings, 2 valid riders ahead (5 board at the destination); one of the two already has a promised ETA in the past (07:40). A false push costs those 2; a suppressed one leaves them 10 min off. The real cost of my call lands on Priya at the review: the figure won't match the on-time commitment, and I'd rather she hear that now.
- **What would flip it.** A dispatch log showing V-10 left at 07:05, or a ping before 07:15 away from the origin. A written instruction from Priya that the commitment overrides measurement would change what is displayed externally, not the measurement or the push.

### D4. Route 14 is NO_VERDICT, though the bus was probably fine
- **Rule.** Position and time come from `recorded_at`; what was knowable comes from `received_at ≤ as-of`. A last update older than 8 min means no verdict.
- **Evidence.** V-04's first 52 pings have normal 3 s delivery. From 06:57:13 all 145 remaining pings are offset by exactly 5,400 s and were received 08:27 to 09:14, after 07:45. On the device clock the bus was −0.0 to +0.7 min all the way (19.4 of 22.6 km at 07:44:46). That is hindsight, not knowable at 07:45.
- **Where it breaks.** HOLD would have been correct. A constant offset looks like an ingest-clock fault and not a transmission delay, so those pings may have been available live. I can't verify that from the file.
- **Cost.** Wrong HOLD on a bus that vanished: 12 bookings uninformed. Wrong blank: one question to the data team.
- **What would flip it.** Ingest logs showing the 145 pings were available before 07:45 → HOLD (+0.6 min). **This is the call I am least sure of.**

### D5. Route 17 is NO_VERDICT, not CALL_DRIVER and not "early"
- **Rule.** Stale > 8 min → NO_VERDICT even if the last known state is alarming.
- **Evidence.** V-05 ran steadily ahead of the timetable (−3.0 min at 4.8 km, −6.0 at 9.6 km, −9.2 at 14.6 km), then slowed from 21 to 5 km/h at 14.57 km, which is the Dadar TT stop (14.56 km), and went silent at 07:27:40.
- **Where it breaks.** Three causes give three actions: holding at a timing point until the 07:36 slot (HOLD), a dead device (check the feed), a breakdown (call). I can't separate them.
- **Cost.** 16 bookings; 6 are ahead of the bus (3 valid). All 6 have a promised ETA already in the past, because 6 of 16 TRIP_017 promises are 9.0 to 37.8 min earlier than the timetable. A false CALL costs one phone call; a false HOLD leaves 3 riders with no information.
- **What would flip it.** Any ping after 07:27:40, or the driver.

### D6. Route 21 is HOLD, and operator 7 is included, not dropped
- **Rule.** I applied one data-quality standard to every vehicle. V-09 (operator 7) passes: 40 known pings, 20 s cadence, 3 s median delivery delay, last ping 5 s old, delay +1.0 min.
- **The HANDOFF rule.** Dropping operator 7 would delete a live trip (TRIP_019, 6 bookings, 2 valid ahead) from the table with no evidence it is unreliable. The verdict is HOLD either way (V-03 is at −0.3), so the rule changes nothing here except visibility.
- **Where it breaks.** 40 pings can't prove a vehicle in an "onboarding window" is reliable.
- **Cost.** Hiding it risks a missed problem; including it risks trusting new telemetry. I include it and flag it.
- **What would flip it.** Evidence V-09's positions diverge from reality, in which case that trip becomes NO_VERDICT, not omitted.

### D7. Route 9 is HOLD, and the data-cleaning rules behind every verdict
- **Rule.** Dedupe by content (vehicle, `recorded_at`, lat, lon), never by `ping_id`. P-0002821 is used twice: once by V-05 on Tuesday and once for a replay of a V-11 ping at 07:39:17. Reject pings outside the Mumbai box or off-route by > 300 m: P-0003148, 3149, 3150 are V-11 teleports at 6,500 to 7,800 km/h. Quarantine unparseable timestamps: P-0001797 reads `06:60:23` but was received at 06:42:24, so I quarantined it rather than guess.
- **Where it breaks.** A real far-off ping would be rejected too.
- **Cost.** Negligible; none of these touch a verdict.
- **What would flip it.** Nothing in this extract.

### D8. Thresholds and the clock rule
- **Rule.** ±3 min; stale at 8 min; "not departed" at 10 min; push needs confidence ≥ 0.6. A vehicle whose clock or ingest offset exceeds 15 min is excluded, not re-timed.
- **Basis.** History's widest completed trip was +2.3 min. Running the engine every 10 min on Monday and Tuesday gives **131 HOLD and 1 NO_VERDICT out of 132 queries, with 0 false pushes and 0 false calls**. The one blank is Monday 06:40 on Route 11, the minute the bus starts.
- **Where it breaks.** An earlier version of my engine re-timed a vehicle by arrival time. On V-04 it would have read the bus 90 min late once its later pings arrived. I fixed it. Also, my first run of this engine called Route 11 "late 59.0 min" at 0.95 confidence, the exact confidently-wrong number Priya warned about.
- **What would flip it.** Wednesday-like days appearing in history with 3 to 5 min delays, which would justify a wider threshold.

## Data issues (all verified in the files)
1 unparseable timestamp; 1 id collision and replay; 3 teleport pings and 1 negative speed (P-0003995); V-04's exact 5,400 s offset on 145 pings; V-05's silence; 41 of 201 bookings boarding at the destination; 12 corrupt promised ETAs, all on Wednesday (TRIP_017: 6, TRIP_018: 6).

## Not done
No forecast of arrival at a rider's stop. No learned segment speeds: history shows none are needed, but it is only 12 trips.
