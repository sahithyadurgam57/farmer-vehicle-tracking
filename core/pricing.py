"""AI FEATURE 2 - rental price prediction (uses model trained in ml/train_price_model.py)."""
import os, json, joblib, pandas as pd
from core.constants import season_of
ML = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml", "models")
_model = None
def _load():
    global _model
    if _model is None:
        p = os.path.join(ML, "price_model.joblib")
        if not os.path.exists(p): raise FileNotFoundError("Run: python ml/train_price_model.py")
        _model = joblib.load(p)
    return _model
def metrics():
    with open(os.path.join(ML, "metrics.json")) as f: return json.load(f)
def predict_price(vehicle_type, horsepower, location, crop, activity, duration_hours, month, distance_km, demand=0.6):
    m = metrics(); season = season_of(month)
    X = pd.DataFrame([dict(vehicle_type=vehicle_type, location=location, crop=crop, activity=activity, season=season,
                           horsepower=horsepower, duration_hours=duration_hours, demand=demand, distance_km=distance_km)])
    price = float(_load().predict(X)[0]); mae = m["results"][m["best_model"]]["MAE"]
    low, high = max(0, price - mae), price + mae
    conf = max(0.0, min(0.99, 1 - mae / max(price, 1)))
    factors = [(k, v) for k, v in sorted(m["importance"].items(), key=lambda kv: -kv[1])[:4]]
    return {"low": round(low, -1), "expected": round(price, -1), "high": round(high, -1),
            "confidence": round(conf * 100), "season": season, "factors": factors}
