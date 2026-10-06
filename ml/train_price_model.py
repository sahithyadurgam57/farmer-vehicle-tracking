"""Train + compare 3 regressors, save the best pipeline and metrics."""
import os, sys, json, joblib, numpy as np, pandas as pd
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(ROOT))
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from ml.generate_data import generate

CAT = ["vehicle_type", "location", "crop", "activity", "season"]
NUM = ["horsepower", "duration_hours", "demand", "distance_km"]

def main():
    csv = os.path.join(ROOT, "data", "rental_prices.csv")
    if not os.path.exists(csv):
        generate().to_csv(csv, index=False)
    df = pd.read_csv(csv)
    X, y = df[CAT + NUM], df["price"]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
    models = {"Linear Regression": LinearRegression(),
              "Random Forest": RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1),
              "Gradient Boosting": GradientBoostingRegressor(random_state=42)}
    results, fitted = {}, {}
    for name, m in models.items():
        pipe = Pipeline([("prep", ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), CAT)], remainder="passthrough")),
                         ("model", m)]).fit(Xtr, ytr)
        pred = pipe.predict(Xte)
        results[name] = {"MAE": round(float(mean_absolute_error(yte, pred)), 1),
                         "RMSE": round(float(np.sqrt(mean_squared_error(yte, pred))), 1),
                         "R2": round(float(r2_score(yte, pred)), 4)}
        fitted[name] = (pipe, pred)
        print(f"{name:20s}", results[name])
    best = min(results, key=lambda k: results[k]["RMSE"])
    pipe, pred = fitted[best]
    names = pipe.named_steps["prep"].get_feature_names_out()
    imp = getattr(pipe.named_steps["model"], "feature_importances_", None)
    importance = {}
    if imp is not None:
        for n, v in zip(names, imp):
            col = n.split("__", 1)[1]
            base = next((c for c in CAT if col.startswith(c)), col)
            importance[base] = importance.get(base, 0) + float(v)
    joblib.dump(pipe, os.path.join(ROOT, "models", "price_model.joblib"))
    pd.DataFrame({"actual": yte.values[:200], "predicted": np.round(pred[:200])}).to_csv(
        os.path.join(ROOT, "models", "actual_vs_predicted.csv"), index=False)
    json.dump({"best_model": best, "results": results, "importance": importance,
               "n_train": len(Xtr), "n_test": len(Xte),
               "note": "Trained on simulated/historical-style rental data; retrain with real bookings later."},
              open(os.path.join(ROOT, "models", "metrics.json"), "w"), indent=2)
    print("Best model:", best)

if __name__ == "__main__":
    main()
