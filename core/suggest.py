"""AI FEATURE 3 - plain-language smart suggestions for farmers."""
from core.recommend import required_hp
def smart_suggestions(req, results, price=None):
    s = []
    hp = required_hp(req["acres"])
    s.append(f"🌾 For your {req['acres']:g}-acre {req['crop'].lower()} field, a tractor of about {hp}–{hp + 10} HP is recommended.")
    if price: s.append(f"💰 Estimated rental price is ₹{price['low']:,.0f}–₹{price['high']:,.0f} (expected ₹{price['expected']:,.0f}).")
    good = [r for r in results if r["score"] >= 60 and r["available"]]
    near10 = [r for r in good if r["distance_km"] <= 10]
    s.append(f"📍 There are {len(near10)} suitable available vehicle(s) within 10 km and {len(good)} within your search radius.")
    rated = [r for r in good if r["reviews"]]
    if rated:
        b = max(rated, key=lambda r: r["rating"]); s.append(f"⭐ Highest-rated suitable vehicle: {b['brand']} {b['model']} ({b['rating']}★), {b['distance_km']} km away.")
    s.append("📅 Booking early gives you more vehicle options, especially in the Kharif season (Jun–Oct).")
    return s
