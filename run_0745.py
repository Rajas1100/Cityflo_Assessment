#!/usr/bin/env python3
"""run_0745.py - produce the 07:45 verdict for every route on the REAL bundle and save table, JSON and dashboard cards.

    python run_0745.py [--ts "2026-06-17 07:45:00"] [--data ./data]
"""
import argparse, json, warnings
import pandas as pd
from route_status_mvp import RouteStatusEngine
warnings.filterwarnings("ignore")
ap = argparse.ArgumentParser(); ap.add_argument("--ts", default="2026-06-17 07:45:00"); ap.add_argument("--data", default="./data")
a = ap.parse_args()
e = RouteStatusEngine(a.data)
out = {rid: e.get_route_status(rid, a.ts) for rid in e.geoms}
rows = [dict(route=rid, name=e.geoms[rid].name, verdict=d["verdict"]["label"], engine_status=d["status"], delay_min=d["delay_minutes"],
             confidence=d["confidence"], reason=d["verdict"]["reason"]) for rid, d in out.items()]
T = pd.DataFrame(rows)
print(T.to_string(index=False))
json.dump(out, open("results_real/verdicts_0745.json", "w"), indent=2, default=str)
T.to_csv("results_real/verdict_table_0745.csv", index=False)
open("results_real/dashboard_cards_0745.txt", "w").write("\n\n".join(d["dashboard"]["text"] for d in out.values()) + "\n")
print("\nquarantined rows:", e.quarantine)
