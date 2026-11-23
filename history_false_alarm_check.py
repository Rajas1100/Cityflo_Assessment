#!/usr/bin/env python3
"""history_false_alarm_check.py - run the engine every 10 min on the two NORMAL mornings (Mon 15, Tue 16 June) for all routes.

On those days every completed trip finished within -1.7..+2.3 min of the timetable and none was 3+ min late, so any
non-HOLD verdict is a candidate false alarm.   python history_false_alarm_check.py [--data ./data]
"""
import argparse, warnings
import pandas as pd
from route_status_mvp import RouteStatusEngine
warnings.filterwarnings("ignore")
ap = argparse.ArgumentParser(); ap.add_argument("--data", default="./data"); a = ap.parse_args()
e = RouteStatusEngine(a.data)
rows = []
for day in ("2026-06-15", "2026-06-16"):
    for t in pd.date_range(f"{day} 06:30", f"{day} 08:10", freq="10min"):
        for rid in e.geoms:
            d = e.get_route_status(rid, t)
            rows.append(dict(day=day[-2:], t=t.strftime("%H:%M"), route=rid, verdict=d["verdict"]["code"], reason=d["verdict"]["reason"]))
R = pd.DataFrame(rows)
print("queries:", len(R), "| verdicts:", R.verdict.value_counts().to_dict())
bad = R[R.verdict != "HOLD"]
print("non-HOLD:", len(bad))
for r in bad.itertuples():
    print(f"  {r.day} {r.t} route {r.route}: {r.verdict}: {r.reason}")
print("false PUSH_LATE:", int((R.verdict == "PUSH_LATE").sum()), "| false CALL_DRIVER:", int((R.verdict == "CALL_DRIVER").sum()))
