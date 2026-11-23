# Route lateness: "is route X running late right now, and by how much?"

Cityflo data take-home. Reads the real bundle (`data/`), reconstructs each route's timeline, compares actual with expected
progress, and returns a verdict per route (`PUSH_LATE n min` / `HOLD` / `CALL_DRIVER` / `NO_VERDICT`) with a plain-language
dashboard card.

Start with **[DECISION_RECORD.md](DECISION_RECORD.md)** (the 07:45 verdicts and the defence of each call), then
**[SUBMISSION_NARRATIVE.md](SUBMISSION_NARRATIVE.md)**.

## 07:45 on 2026-06-17 (real data)

| Route | Verdict | Why |
|---|---|---|
| 11 Borivali → BKC | CALL_DRIVER | V-06 has not left the origin, 59 min past departure, GPS fresh |
| 17 Vashi → Worli | NO_VERDICT | V-05 silent for 17 min after running up to 9 min early |
| 12 Mulund → Andheri E | PUSH_LATE 10 min | V-10 left at 07:15 for a 07:05 departure, delay flat at 10.0 |
| 14 Kandivali → Lower Parel | NO_VERDICT | V-04's feed is 48 min stale; 145 pings carry a 5,400 s offset |
| 21 Ghatkopar → BKC | HOLD | both trips on the timetable; riders on TRIP_018 were shown ETAs 19 min early |
| 9 Thane → Powai | HOLD | trip arrived on time |

Worry-order: 11, 17, 12, 14, 21, 9. Two `HANDOFF.md` reconciliation rules (zero Route 12, drop operator 7) were **not** applied;
see D3 and D6.

## Quickstart

The Cityflo bundle is not committed. Download `routes`, `stops`, `trips`, `bookings` and `gps_pings` `.csv` from
https://careers.cityflo.com/takehomes/data-engineer/ into `./data/`.

```bash
pip install -r requirements.txt
python run_0745.py                      # verdict table, JSON and cards -> results_real/
python real_data_analysis.py            # the evidence behind every number in the record
python history_false_alarm_check.py     # 132 queries on the two normal mornings: 0 false pushes or calls
```
```python
from route_status_mvp import RouteStatusEngine
e = RouteStatusEngine("./data")
e.get_route_status(12, "2026-06-17 07:45:00")["verdict"]
```

## Layout

| Path | What it is |
|---|---|
| `DECISION_RECORD.md`, `SUBMISSION_NARRATIVE.md` | The graded write-up |
| `decisions.jsonl` | Steering ledger: verbatim quotes with turn anchors. **Anchors are line numbers in the uploaded raw `session.jsonl`** |
| `route_status_mvp.py`, `dashboard_explain.py` | The engine and the dashboard cards |
| `run_0745.py`, `real_data_analysis.py`, `history_false_alarm_check.py` | Real-data scripts |
| `data/` | Where the Cityflo bundle goes (git-ignored, not redistributed) |
| `results_real/` | Saved outputs of the real-data scripts |
| `cityflo_dummy_data/`, `generate_dummy_data.py`, `validation_scenarios.py`, `false_late_probes.py`, `dashboard_checks.py`, `dataset_analysis.py`, `results/` | Synthetic test harness: 14 scenario tests, 9 false-late probes, 50 card checks. Edge-case fixtures only; no real-data finding comes from them |
| `docs/` | Design notes; the earlier synthetic-data narrative (archived) |

## Known weaknesses

8 of 9 synthetic false-late probes still produce a late label. The 10 min "not departed" rule was written after seeing
Wednesday. Linear timetable and straight-line geometry rest on 12 history trips. Details in the narrative, Section 8.

Built interactively with an AI assistant (Claude).
