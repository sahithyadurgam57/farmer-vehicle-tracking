# AgriConnect AI – Project Report Outline
1. **Abstract** – AI-assisted platform connecting farmers with nearby agricultural vehicle owners.
2. **Problem Statement** – Farmers struggle to find suitable machinery at the right time/price; owners struggle to find customers.
3. **Existing System** – Phone calls, local brokers, no price transparency.
4. **Proposed System** – Web platform with recommendation, price prediction, booking, owner/admin modules.
5. **Objectives / Features** – See README.
6. **Architecture** – Streamlit UI → `core/` services → SQLite; `ml/` trains model → `ml/models/*.joblib` → `core/pricing.py`.
7. **Technology** – Python 3.12, Streamlit, SQLite, pandas, scikit-learn, joblib.
8. **Database** – users, vehicles, bookings, reviews, notifications, favorites, complaints, vehicle_types, ai_logs (see `core/db.py`).
9. **AI Architecture** – Rule-based explainable scoring (recommendation); supervised regression (price); grounded retrieval chatbot.
10. **Dataset** – 3,000 simulated rows: vehicle type, HP, location, crop, activity, duration, season, demand, distance, price.
11. **Evaluation** – MAE, RMSE, R² on 20% hold-out; see Admin → AI Analytics (`ml/models/metrics.json`).
12. **Testing** – Manual flows per role; logic checked via `python seed.py` + scripts.
13. **Limitations** – Simulated data, straight-line distance, no payments/GPS.
14. **Future work** – GPS tracking, weather-aware recommendations, regional languages, SMS/WhatsApp, online payments, demand forecasting.
Add ER/DFD/use-case diagrams and screenshots from the running app.
