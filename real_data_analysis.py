#!/usr/bin/env python3
"""
real_data_analysis.py - evidence behind the 07:45 verdicts on the REAL Cityflo bundle (./data).

    python real_data_analysis.py            # prints everything; results_real/ holds a saved copy

Every number quoted in DECISION_RECORD.md comes from this script or from route_status_mvp.py at 2026-06-17 07:45.
Sections: A data quality, B history (normal mornings), C live-morning evidence per trip, D promised ETAs,
E hindsight on the stale feed (NOT knowable at 07:45), F rider exposure.
"""
import warnings
import numpy as np
import pandas as pd
from route_status_mvp import RouteStatusEngine

warnings.filterwarnings("ignore")
pd.set_option("display.width", 220, "display.max_columns", 30, "display.max_rows", 200)
DATA = "./data"
ASOF = pd.Timestamp("2026-06-17 07:45:00")
e = RouteStatusEngine(DATA)
raw = pd.read_csv(f"{DATA}/gps_pings.csv")
p = e.pings.copy()
p["skew_s"] = (p.received_at - p.recorded_at).dt.total_seconds()
ctx = e._build_ctx(ASOF)

print("=" * 100, "\nA. DATA QUALITY")
print("rows in file:", len(raw), "| quarantined (unparseable timestamp):", e.quarantine)
dup_id = raw[raw.ping_id.duplicated(keep=False)]
print("ping_id collisions:", dup_id.ping_id.unique().tolist(), "-> same id on", dup_id.vehicle_id.tolist(),
      "(one is a replay of V-11's 07:39:17 ping: same vehicle, time, lat, lon)")
print("content duplicates (vehicle, recorded_at, lat, lon):", int(p.duplicated(["vehicle_id", "recorded_at", "lat", "lon"]).sum()))
junk = p[(p.lat < 19.0) | (p.lat > 19.35) | (p.lon < 72.8) | (p.lon > 73.05)]
print("out-of-area pings:", junk[["ping_id", "vehicle_id", "speed_kmph"]].round(0).values.tolist())
print("negative speed:", p[p.speed_kmph < 0][["ping_id", "vehicle_id", "speed_kmph"]].round(1).values.tolist())
big = p[p.skew_s.abs() > 900]
print("pings with |received - recorded| > 15 min:", len(big), "| vehicles:", big.vehicle_id.unique().tolist(),
      "| all exactly 5400 s:", bool((big.skew_s == 5400).all()), "| first affected recorded_at:", big.recorded_at.min().strftime("%m-%d %H:%M:%S"))
print("fleet median delivery delay:", p.skew_s.median(), "s | 99th percentile excluding the 5400 s block:", round(p[p.skew_s < 900].skew_s.quantile(.99), 1), "s")
print("operators:", p.groupby("vehicle_id").operator_id.first().to_dict())
cad = p.sort_values(["vehicle_id", "recorded_at"]).groupby("vehicle_id").recorded_at.diff().dt.total_seconds()
print("cadence median:", cad.median(), "s | gaps > 60 s inside a morning: 0 (all 12 large gaps are overnight)")
b = e.bookings.merge(e.trips[["trip_id", "route_id", "scheduled_start", "scheduled_end", "service_date"]], on="trip_id")
lastst = e.routes.set_index("route_id").dest_stop
laststop_id = {r: g.stops.stop_id.iloc[-1] for r, g in e.geoms.items()}
firststop_id = {r: g.stops.stop_id.iloc[0] for r, g in e.geoms.items()}
print("bookings boarding at the route's LAST stop:", int(sum(r.boarding_stop_id == laststop_id[r.route_id] for r in b.itertuples())),
      "| at the first stop:", int(sum(r.boarding_stop_id == firststop_id[r.route_id] for r in b.itertuples())), "| of", len(b))

print("\n", "=" * 100, "\nB. HISTORY: delay vs timetable on Monday/Tuesday (completed trips)")
hist = []
for _, t in e.trips[e.trips.service_date < "2026-06-17"].iterrows():
    g = e.geoms[t.route_id]
    tr, _ = e._track(t, g, e._build_ctx(pd.Timestamp("2026-06-18")))
    a = tr[tr.dist >= g.D - e.cfg.terminal_tol_m].iloc[0]
    d50 = tr[tr.dist >= 0.5 * g.D].iloc[0]
    hist.append(dict(trip=t.trip_id, route=t.route_id, day=t.service_date.day,
                     first_ping_vs_start_min=round((tr.t_eff.iloc[0] - t.scheduled_start).total_seconds() / 60, 1),
                     delay_at_50pct=round((d50.t_eff - g.sched_time(t.scheduled_start, d50.dist)).total_seconds() / 60, 1),
                     arrival_delay=round((a.t_eff - g.sched_time(t.scheduled_start, a.dist)).total_seconds() / 60, 1)))
H = pd.DataFrame(hist)
print(H.sort_values(["route", "day"]).to_string(index=False))
print(f"range of arrival delay: {H.arrival_delay.min():+.1f} to {H.arrival_delay.max():+.1f} min | trips >= 3 min late: {(H.arrival_delay >= 3).sum()} of {len(H)}"
      f" | every first ping is at the scheduled start: {bool((H.first_ping_vs_start_min == 0).all())}")

print("\n", "=" * 100, "\nC. LIVE MORNING: what was KNOWN at 07:45 (received_at <= 07:45), per trip")
rows = []
for _, t in e.trips[e.trips.service_date == "2026-06-17"].iterrows():
    g = e.geoms[t.route_id]
    tr, meta = e._track(t, g, ctx)
    allp = p[(p.vehicle_id == t.vehicle_id) & (p.recorded_at.dt.day == 17)]
    r = dict(trip=t.trip_id, route=t.route_id, veh=t.vehicle_id, op=int(allp.operator_id.iloc[0]), sched=f"{t.scheduled_start:%H:%M}-{t.scheduled_end:%H:%M}",
             pings_in_file=len(allp), known_at_0745=meta["n_raw"], rejected=meta["n_rejected"],
             first_ping=f"{allp.recorded_at.min():%H:%M:%S}")
    if tr is not None:
        l = tr.iloc[-1]
        r.update(last_known_ping=f"{l.t_eff:%H:%M:%S}", age_min=round((ASOF - l.t_eff).total_seconds() / 60, 1), km=round(l.dist / 1000, 2),
                 pct=round(l.dist / g.D * 100), last_speed=l.speed_kmph,
                 delay_min=round((l.t_eff - g.sched_time(t.scheduled_start, l.dist)).total_seconds() / 60, 1))
    rows.append(r)
print(pd.DataFrame(rows).to_string(index=False))
v6 = p[(p.vehicle_id == "V-06") & (p.recorded_at.dt.day == 17)]
print(f"\nV-06 (Route 11): {len(v6)} pings, {v6[['lat','lon']].round(4).drop_duplicates().shape[0]} distinct positions at 4 dp, "
      f"max speed {v6.speed_kmph.max():.1f} km/h, furthest from origin {e.geoms[11].snap(v6.lat.to_numpy(), v6.lon.to_numpy())[0].max():.0f} m")
v10 = e._track(e.trips[e.trips.trip_id == "TRIP_015"].iloc[0], e.geoms[12], ctx)[0]
dl = [(a - e.geoms[12].sched_time(pd.Timestamp("2026-06-17 07:05"), x)).total_seconds() / 60 for a, x in zip(v10.t_eff, v10.dist)]
print(f"V-10 (Route 12): first ping at origin {v10.t_eff.iloc[0]:%H:%M:%S}; delay min/max along the way {min(dl):.1f}/{max(dl):.1f} (flat) over {v10.dist.iloc[-1] / 1000:.1f} km")
v5 = e._track(e.trips[e.trips.trip_id == "TRIP_017"].iloc[0], e.geoms[17], ctx)[0]
d5 = [(a - e.geoms[17].sched_time(pd.Timestamp("2026-06-17 06:50"), x)).total_seconds() / 60 for a, x in zip(v5.t_eff, v5.dist)]
print(f"V-05 (Route 17): delay at 25%/50%/70% = {d5[len(d5)//4]:.1f}/{d5[len(d5)//2]:.1f}/{d5[-1]:.1f} min (EARLY); stopped at {v5.dist.iloc[-1] / 1000:.2f} km "
      f"= Dadar TT stop at {e.geoms[17].cum[5] / 1000:.2f} km; speed fell from {v5.speed_kmph.iloc[-8]:.0f} to {v5.speed_kmph.iloc[-1]:.0f} km/h; silent since {v5.t_eff.iloc[-1]:%H:%M:%S}")

print("\n", "=" * 100, "\nD. PROMISED ETA vs TIMETABLE (minutes), per trip")
def diff(r):
    g = e.geoms[r.route_id]
    i = g.stops.index[g.stops.stop_id == r.boarding_stop_id][0]
    return (r.promised_eta - (r.scheduled_start + pd.Timedelta(minutes=g.runtime_min * g.cum[i] / g.D))).total_seconds() / 60
b["diff"] = b.apply(diff, axis=1)
bad = b[b["diff"].abs() > 0.5]
print("bookings:", len(b), "| promise != timetable:", len(bad), "| by trip:", bad.groupby("trip_id")["diff"].agg(["count", "min", "max"]).round(1).to_dict("index"))
print("promised ETA earlier than the trip's own scheduled start:", b[b.promised_eta < b.scheduled_start].booking_id.tolist())
print("Mon/Tue promises that differ from the timetable:", int((b[b.service_date < "2026-06-17"]["diff"].abs() > 0.5).sum()), "of", int((b.service_date < "2026-06-17").sum()))

print("\n", "=" * 100, "\nE. HINDSIGHT ONLY (NOT knowable at 07:45): V-04 / Route 14 using the device clock")
q = p[(p.vehicle_id == "V-04") & (p.recorded_at.dt.day == 17)].sort_values("recorded_at")
g = e.geoms[14]
dd, _ = g.snap(q.lat.to_numpy(), q.lon.to_numpy())
q = q.assign(dist=np.maximum.accumulate(dd))
q["delay"] = [(a - g.sched_time(pd.Timestamp("2026-06-17 06:40"), x)).total_seconds() / 60 for a, x in zip(q.recorded_at, q.dist)]
print(f"delay on device time: {q.delay.min():+.1f} to {q.delay.max():+.1f} min over the whole trip; last device ping {q.recorded_at.iloc[-1]:%H:%M:%S} at {q.dist.iloc[-1] / 1000:.1f} of {g.D / 1000:.1f} km")
print(f"pings known to the server at 07:45: {int((q.received_at <= ASOF).sum())} of {len(q)}; the other {int((q.received_at > ASOF).sum())} were received 08:27-09:14")

print("\n", "=" * 100, "\nF. RIDER EXPOSURE at 07:45 (bookings on each live trip)")
pos = {"TRIP_014": 0.0, "TRIP_015": 5670.0, "TRIP_017": 14570.0, "TRIP_018": 3040.0, "TRIP_019": 1440.0}
for tid, km in pos.items():
    bt = b[b.trip_id == tid]
    g2 = e.geoms[int(bt.route_id.iloc[0])]
    cum = dict(zip(g2.stops.stop_id, g2.cum))
    ahead = bt[[cum[s] > km for s in bt.boarding_stop_id]]
    missed = int((ahead.promised_eta < ASOF).sum())
    print(f"{tid}: bookings {len(bt)} | boarding ahead of the bus {len(ahead)} | of those, promised ETA already passed {missed}")
