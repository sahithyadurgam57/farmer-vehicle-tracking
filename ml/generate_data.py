"""Create SIMULATED rental-price data (no real dataset is available for this academic project)."""
import numpy as np, pandas as pd, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.constants import ACTIVITY_VEHICLES, CROP_ACTIVITIES, LOCATIONS, season_of

BASE_HOURLY = {"Tractor": 350, "Harvester": 1400, "Combine Harvester": 2200, "Rotavator": 450,
               "Cultivator": 300, "Seed Drill": 380, "Plough": 280, "Thresher": 600, "Sprayer": 320,
               "Tiller": 330, "Trailer": 260, "Paddy Transplanter": 700}
LOC_FACTOR = dict(zip(LOCATIONS, [1.0, 1.08, 0.97, 0.95, 0.93, 1.0, 0.96, 0.92, 0.9, 1.0, 0.95, 1.15]))
SEASON_FACTOR = {"Kharif": 1.12, "Rabi": 1.05, "Summer": 0.92}

def generate(n=3000, seed=42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n):
        act = str(rng.choice(list(ACTIVITY_VEHICLES)))
        vt = str(rng.choice(ACTIVITY_VEHICLES[act]))
        crops = [c for c, a in CROP_ACTIVITIES.items() if act in a] or list(CROP_ACTIVITIES)
        crop = str(rng.choice(crops))
        loc = str(rng.choice(list(LOCATIONS)))
        month = int(rng.integers(1, 13)); season = season_of(month)
        big = vt in ("Tractor", "Combine Harvester", "Harvester")
        hp = int(rng.choice([35, 40, 45, 50, 55, 60, 75])) if big else int(rng.choice([20, 30, 40]))
        hours = int(rng.choice([2, 4, 6, 8, 10, 16]))
        demand = float(np.clip(rng.normal(0.55 + (0.2 if season == "Kharif" else 0), 0.18), 0.05, 1.0))
        dist = float(np.round(rng.uniform(1, 45), 1))
        rate = BASE_HOURLY[vt] * (1 + (hp - 45) / 250) * LOC_FACTOR[loc] * SEASON_FACTOR[season] * (0.85 + 0.4 * demand)
        price = (rate * hours * (0.92 if hours >= 8 else 1.0) + dist * 14) * rng.normal(1, 0.05)
        rows.append([vt, hp, loc, crop, act, hours, season, round(demand, 2), dist, round(price / 10) * 10, month])
    return pd.DataFrame(rows, columns=["vehicle_type", "horsepower", "location", "crop", "activity",
                                       "duration_hours", "season", "demand", "distance_km", "price", "month"])

if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "rental_prices.csv")
    df = generate(); df.to_csv(out, index=False); print("Saved", len(df), "rows ->", out)
