"""AI FEATURE 1 - explainable vehicle recommendation (weighted scoring, weights are editable)."""
from core.constants import ACTIVITY_VEHICLES, CROP_ACTIVITIES
from core.geo import haversine_km, travel_minutes
from core import db
WEIGHTS = {"requirement": 0.30, "distance": 0.20, "price": 0.15, "availability": 0.15, "rating": 0.10, "performance": 0.10}

def required_hp(acres: float) -> int:
    return int(30 + 4 * min(acres, 10))

def _clip(x): return max(0.0, min(1.0, x))

def score_vehicle(v, req, weights=None):
    w = weights or WEIGHTS
    km = haversine_km(req["lat"], req["lon"], v["latitude"], v["longitude"])
    days = req["duration_hours"] / 8
    rent = min(v["price_per_hour"] * req["duration_hours"], v["price_per_day"] * max(1, -(-req["duration_hours"] // 8))) 
    # requirement match
    type_ok = v["vehicle_type"] in ACTIVITY_VEHICLES.get(req["activity"], [])
    crop_ok = req["activity"] in CROP_ACTIVITIES.get(req["crop"], [])
    hp_need = required_hp(req["acres"])
    hp_fit = 1.0 if v["horsepower"] >= hp_need else _clip(v["horsepower"] / hp_need)
    if v["vehicle_type"] in ("Tractor", "Combine Harvester", "Harvester"):
        req_match = (0.6 if type_ok else 0.0) + 0.2 * (1 if crop_ok else 0.5) + 0.2 * hp_fit
    else:
        req_match = (0.75 if type_ok else 0.0) + 0.25 * (1 if crop_ok else 0.5)
    dist = _clip(1 - km / 50)
    budget = req["budget"] or 0
    price = 1.0 if not budget else (1.0 if rent <= budget else _clip(1 - (rent - budget) / budget))
    booked = db.is_booked(v["id"], req["date"])
    avail = 0.0 if (booked or v["availability_status"] != "Available") else 1.0
    rating, n = db.vehicle_rating(v["id"]); rating_s = rating / 5 if n else 0.7
    perf = _clip(v["horsepower"] / 75) if v["horsepower"] else 0.5
    parts = {"requirement": req_match, "distance": dist, "price": price, "availability": avail, "rating": rating_s, "performance": perf}
    total = sum(parts[k] * w[k] for k in parts)
    why = []
    if type_ok: why.append(f"suitable for {req['activity'].lower()} on your {req['acres']:g}-acre {req['crop'].lower()} field")
    if hp_fit >= 1 and v["vehicle_type"] == "Tractor": why.append(f"{v['horsepower']} HP meets the ~{hp_need} HP needed")
    why.append("available on your date" if avail else "NOT available on your date")
    why.append(f"only {km} km away")
    if budget: why.append(f"within your budget (₹{rent:,.0f})" if rent <= budget else f"₹{rent - budget:,.0f} above your budget")
    return {**v, "score": round(total * 100), "parts": {k: round(p * 100) for k, p in parts.items()}, "distance_km": km,
            "travel_min": travel_minutes(km), "rent_estimate": round(rent), "rating": rating, "reviews": n,
            "available": bool(avail), "suitable": type_ok, "why": "Recommended because it is " + ", ".join(why) + "." if type_ok else
            "Weak match: this vehicle type is not typical for " + req["activity"].lower() + "."}

def recommend(req, max_km=50, weights=None):
    vs = db.q("SELECT v.*, u.name owner_name FROM vehicles v JOIN users u ON u.id=v.owner_id WHERE u.verification_status='verified'")
    out = [score_vehicle(v, req, weights) for v in vs]
    out = [o for o in out if o["distance_km"] <= max_km and o["suitable"]]  # hide vehicles that cannot do the job
    out.sort(key=lambda o: -o["score"])
    if out:
        out[0]["badges"] = ["🤖 AI Recommended"]
        for o in out: o.setdefault("badges", [])
        near = min(out, key=lambda o: o["distance_km"]); near["badges"].append("📍 Nearest")
        valid = [o for o in out if o["score"] >= 50]
        if valid:
            bv = max(valid, key=lambda o: o["score"] / max(o["rent_estimate"], 1)); bv["badges"].append("🏆 Best Value")
        rated = [o for o in out if o["reviews"] and o["rating"] >= 4.5]
        if rated: max(rated, key=lambda o: o["rating"])["badges"].append("⭐ Top Rated")
    return out
