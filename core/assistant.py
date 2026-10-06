"""AI FEATURE 4 - AgriAssist: answers ONLY from database facts. Optional Ollama only rewords them."""
import re, json, urllib.request
from core import db
from core.constants import VEHICLE_TYPES, ACTIVITY_VEHICLES, LOCATIONS
from core.geo import haversine_km
KEYWORDS = {"harvest": "Combine Harvester", "combine": "Combine Harvester", "tractor": "Tractor", "rotavator": "Rotavator",
            "cultivator": "Cultivator", "sprayer": "Sprayer", "plough": "Plough", "thresher": "Thresher", "seed": "Seed Drill",
            "transplant": "Paddy Transplanter", "trailer": "Trailer", "tiller": "Tiller"}
def _ollama(prompt, model="llama3.2"):
    try:
        req = urllib.request.Request("http://localhost:11434/api/generate", method="POST",
              data=json.dumps({"model": model, "prompt": prompt, "stream": False}).encode(), headers={"Content-Type": "application/json"})
        return json.loads(urllib.request.urlopen(req, timeout=20).read())["response"].strip()
    except Exception:
        return None
def answer(text, user, use_ollama=False):
    t = text.lower(); lat, lon = user.get("latitude") or 16.3067, user.get("longitude") or 80.4365
    vt = next((v for k, v in KEYWORDS.items() if k in t), None)
    m = re.search(r"(?:₹|rs\.?\s*|budget\s*(?:of)?\s*)(\d[\d,]*)", t); budget = int(m.group(1).replace(",", "")) if m else None
    vs = db.q("SELECT * FROM vehicles WHERE availability_status='Available'")
    for v in vs: v["km"] = haversine_km(lat, lon, v["latitude"], v["longitude"])
    if vt: vs = [v for v in vs if v["vehicle_type"] == vt]
    if budget: vs = [v for v in vs if v["price_per_day"] <= budget]
    if "near" in t or "nearest" in t: vs.sort(key=lambda v: v["km"])
    else: vs.sort(key=lambda v: (v["km"], v["price_per_day"]))
    if not vs: return "I couldn't find matching available vehicles in the platform right now. Try a different budget or vehicle type."
    lines = [f"• {v['brand']} {v['model']} ({v['vehicle_type']}, {v['horsepower']} HP) – ₹{v['price_per_day']:,.0f}/day – {v['km']} km away – {v['location']}" for v in vs[:5]]
    facts = "Matching available vehicles (live data):\n" + "\n".join(lines)
    if use_ollama:
        r = _ollama("You are AgriAssist. Using ONLY these facts (never invent prices or availability), answer the farmer's question briefly.\n"
                    f"Facts:\n{facts}\nQuestion: {text}")
        if r: return r + "\n\n" + facts
    return facts + "\n\nAsk me about a budget (e.g. 'I have ₹5000, what can I book?') or a vehicle type."
