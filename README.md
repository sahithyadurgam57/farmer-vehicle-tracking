# 🚜 AgriConnect AI — Smart Agricultural Vehicle Booking & Recommendation Platform
*The Right Vehicle. The Right Price. At the Right Time.*

Streamlit + SQLite + scikit-learn college project. Roles: Farmer, Vehicle Owner, Admin.

## Run it (Python 3.12)
```bash
python -m venv venv
venv\Scripts\activate          # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
python seed.py                           # creates agriconnect.db with SAMPLE data
python ml/generate_data.py               # 3,000 simulated rental records
python ml/train_price_model.py           # compares 3 models, saves the best
streamlit run app.py
```
(`app.py` also seeds/trains automatically on first run if they are missing.)

**Demo logins** (password `Demo@123`): `farmer@demo.com`, `owner@demo.com`, `admin@demo.com`

## The 4 AI features (all in `core/`, separate from normal app code)
| Feature | File | How it works |
|---|---|---|
| Vehicle recommendation | `recommend.py` | Explainable weighted score: 30% requirement, 20% distance, 15% price, 15% availability, 10% rating, 10% performance (edit `WEIGHTS`). Gives a plain-language "why". Unsuitable vehicle types are filtered out. |
| Price prediction | `pricing.py` + `ml/` | Linear Regression vs Random Forest vs Gradient Boosting; best by RMSE is saved. Low/Expected/High range uses the model's MAE. |
| Smart suggestions | `suggest.py` | Farmer-friendly tips built from the search results and price prediction. |
| AgriAssist chatbot | `assistant.py` | Answers only from database rows (no invented prices). Optional local Ollama (`llama3.2`) only rewords those facts. |

> The initial AI model is trained using simulated/historical-style agricultural rental data. The model can later be retrained using real platform booking data.

## Flow
Register → Find Vehicles (crop, activity, acres, location, date, budget) → AI score + price + suggestions + map → Compare → Book (Pending) → Owner Accepts → Farmer Confirms → Owner Starts → Completed → Review.
Owners must be verified by admin (`owner3@demo.com` is a pending sample).

## Folders
`app.py` UI · `core/` logic (db, auth, geo, recommend, pricing, suggest, assistant) · `ml/` data generator, training, saved model · `docs/` report · `seed.py` demo data

## Scope notes
No payments, live GPS, Docker or microservices. Map uses Streamlit's built-in map (OpenStreetMap-style tiles, no API key); vehicle positions are shown at ~1 km precision, exact location only for active bookings. Browser GPS is not available in plain Streamlit, so farmers pick their town. Passwords use salted PBKDF2.
