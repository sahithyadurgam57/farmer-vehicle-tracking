"""AgriConnect AI - Streamlit app. Run: streamlit run app.py"""
import os, datetime as dt
import pandas as pd, streamlit as st
from core import db, auth, pricing, recommend, suggest, assistant
from core.constants import CROPS, ACTIVITIES, LOCATIONS, VEHICLE_TYPES
from core.geo import haversine_km

st.set_page_config(page_title="AgriConnect AI", page_icon="🚜", layout="wide")
db.init_db()
if not os.path.exists(db.DB_PATH) or not db.q("SELECT 1 FROM users LIMIT 1"):
    import subprocess, sys; subprocess.run([sys.executable, "seed.py"], check=False)
if not os.path.exists(os.path.join(pricing.ML, "price_model.joblib")):
    import subprocess, sys; subprocess.run([sys.executable, "ml/train_price_model.py"], check=False)

st.markdown("""<style>
.hero{background:linear-gradient(135deg,#2E7D32,#9CCC65);color:#fff;padding:2.2rem;border-radius:20px;margin-bottom:1rem}
.hero h1{color:#fff;margin:0}.card{background:#F1F8E9;border:1px solid #C5E1A5;border-radius:16px;padding:1rem;margin-bottom:.8rem}
.badge{background:#FFF59D;border-radius:10px;padding:2px 8px;margin-right:6px;font-size:.85rem}
.stButton>button{border-radius:12px;font-weight:600}
</style>""", unsafe_allow_html=True)

ss = st.session_state
ss.setdefault("user", None)
def logout(): ss.clear()
STATUS_ICON = {"Available": "🟢", "Busy": "🟡", "Maintenance": "🔴", "Offline": "🔴"}
def bar(label, v): st.progress(min(max(v, 0), 100) / 100, text=f"{label}: {v}%")

# ---------------------------------------------------------------- Landing / Auth
def landing():
    st.markdown("""<div class='hero'><h1>🚜 AgriConnect AI</h1><h3>Find the Right Agricultural Vehicle Near You</h3>
    <p>AI-powered vehicle recommendations, smart price prediction and easy booking for farmers.<br>
    <i>The Right Vehicle. The Right Price. At the Right Time.</i></p></div>""", unsafe_allow_html=True)
    c1, c2 = st.columns([3, 2])
    with c1:
        st.subheader("How it works")
        for i, t in enumerate(["Tell us what you need", "AI finds suitable vehicles", "Compare prices and distance",
                               "Book your vehicle", "Complete your farming work"], 1): st.write(f"**{i}.** {t}")
        st.subheader("Why choose us?")
        st.write("🤖 AI Vehicle Recommendation  •  💰 Smart Price Prediction  •  📍 Nearby Vehicle Search  •  "
                 "🔎 Transparent Pricing  •  📅 Easy Booking  •  ✅ Verified Vehicle Owners")
        st.info("Demo logins (sample data): farmer@demo.com, owner@demo.com, admin@demo.com — password Demo@123")
    with c2:
        tab1, tab2 = st.tabs(["Login", "Register"])
        with tab1:
            e = st.text_input("Email", key="le"); p = st.text_input("Password", type="password", key="lp")
            if st.button("Login", type="primary", use_container_width=True):
                u = auth.login(e, p)
                if u: ss.user = u; st.rerun()
                else: st.error("Wrong email or password.")
        with tab2:
            role = st.radio("I am a", ["Farmer", "Vehicle Owner"], horizontal=True)
            n = st.text_input("Full name"); ph = st.text_input("Phone"); em = st.text_input("Email", key="re")
            pw = st.text_input("Password (min 6 chars)", type="password", key="rp"); loc = st.selectbox("Your town", list(LOCATIONS))
            if st.button("Create account", use_container_width=True):
                if not n.strip(): st.error("Please enter your name.")
                else:
                    uid, err = auth.register(n.strip(), ph, em, pw, "farmer" if role == "Farmer" else "owner", loc, *LOCATIONS[loc])
                    if err: st.error(err)
                    else: st.success("Account created! Please login." + (" Admin must verify owner accounts before vehicles are shown." if role != "Farmer" else ""))

# ---------------------------------------------------------------- Farmer
def vehicle_card(v, uid, key):
    st.markdown(f"<div class='card'><b>🚜 {v['brand']} {v['model']}</b> ({v['vehicle_type']}) &nbsp;"
                + "".join(f"<span class='badge'>{b}</span>" for b in v.get("badges", [])) +
                f"<br>⭐ {v['rating'] or 'New'} ({v['reviews']}) &nbsp; 📍 {v['distance_km']} km (~{v['travel_min']} min) &nbsp; "
                f"💰 ₹{v['price_per_day']:,.0f}/day &nbsp; {STATUS_ICON.get(v['availability_status'],'🔴')} {v['availability_status']} &nbsp; ⚡ {v['horsepower']} HP"
                f"<br><b>AI Match: {v['score']}%</b></div>", unsafe_allow_html=True)
    with st.expander("Why this match? / score details"):
        st.write(v["why"])
        for k, lab in [("requirement", "Requirement"), ("distance", "Distance"), ("price", "Price"), ("availability", "Availability"),
                       ("rating", "Rating"), ("performance", "Performance")]: bar(lab, v["parts"][k])
        st.caption(f"Owner: {v['owner_name']}  •  Capacity: {v['capacity']}  •  Reg: {v['registration_number']} (sample data)")
        if st.button("❤️ Add to favorites", key=f"fav{key}"):
            db.run("INSERT OR IGNORE INTO favorites VALUES(?,?)", (uid, v["id"])); st.toast("Saved")

def farmer_find(u):
    st.header("🔎 Find a Vehicle")
    with st.form("req"):
        c = st.columns(3)
        crop = c[0].selectbox("🌾 Crop", CROPS); act = c[1].selectbox("Farming activity", ACTIVITIES)
        acres = c[2].number_input("Land area (acres)", 0.5, 500.0, 5.0, 0.5)
        c = st.columns(4)
        loc = c[0].selectbox("📍 Location", list(LOCATIONS), index=list(LOCATIONS).index(u["location"]) if u["location"] in LOCATIONS else 0)
        date = c[1].date_input("📅 Required date", dt.date.today() + dt.timedelta(days=3))
        hours = c[2].selectbox("Duration (hours)", [2, 4, 6, 8, 10, 16, 24], index=3)
        budget = c[3].number_input("💰 Budget (₹, 0 = no limit)", 0, 200000, 4000, 500)
        c = st.columns(3)
        radius = c[0].selectbox("Within", [5, 10, 25, 50], index=3, format_func=lambda x: f"{x} km")
        sort = c[1].selectbox("Sort by", ["AI Recommended", "Nearest", "Lowest Price", "Highest Rating", "Best Value"])
        minhp = c[2].number_input("Minimum HP (optional)", 0, 120, 0)
        go = st.form_submit_button("Find vehicles", type="primary")
    if go:
        if date < dt.date.today(): st.error("Please select a valid booking date."); return
        la, lo = LOCATIONS[loc]
        req = dict(lat=la, lon=lo, acres=acres, crop=crop, activity=act, duration_hours=hours, budget=budget, date=date)
        res = [r for r in recommend.recommend(req, radius) if r["horsepower"] >= minhp]
        keyf = {"AI Recommended": lambda r: -r["score"], "Nearest": lambda r: r["distance_km"], "Lowest Price": lambda r: r["rent_estimate"],
                "Highest Rating": lambda r: -r["rating"], "Best Value": lambda r: -r["score"] / max(r["rent_estimate"], 1)}[sort]
        res.sort(key=keyf)
        ss.req, ss.res, ss.loc = req, res, loc
    if "res" not in ss: return
    req, res = ss.req, ss.res
    if not res: st.warning(f"No vehicles found within the selected distance. Try a bigger radius."); return
    top_type = res[0]["vehicle_type"]
    price = pricing.predict_price(top_type, res[0]["horsepower"], ss.loc, req["crop"], req["activity"], req["duration_hours"],
                                  req["date"].month, res[0]["distance_km"])
    ss.price = price
    st.subheader("🤖 Smart Suggestions for You")
    for s in suggest.smart_suggestions(req, res, price): st.write(s)
    with st.expander(f"💰 AI price prediction for {top_type} ({req['activity']}, {req['duration_hours']}h)", expanded=True):
        c = st.columns(3); c[0].metric("Low", f"₹{price['low']:,.0f}"); c[1].metric("Expected", f"₹{price['expected']:,.0f}"); c[2].metric("High", f"₹{price['high']:,.0f}")
        st.write(f"Confidence: **{price['confidence']}%**  •  Season: {price['season']}")
        st.caption("Main factors: " + ", ".join(f"{k.replace('_',' ')} ({v*100:.0f}%)" for k, v in price["factors"]))
    st.subheader("📍 Map (approximate vehicle locations)")
    pts = [{"lat": r["latitude"].__round__(2), "lon": r["longitude"].__round__(2)} for r in res]  # privacy: ~1 km precision
    pts.append({"lat": req["lat"], "lon": req["lon"]})
    st.map(pd.DataFrame(pts), zoom=8)
    st.subheader(f"Found {len(res)} vehicle(s)")
    for i, v in enumerate(res): vehicle_card(v, u["id"], i)
    st.subheader("⚖️ Compare")
    names = {f"{r['brand']} {r['model']} ({r['id']})": r for r in res}
    pick = st.multiselect("Choose vehicles to compare", list(names))
    if pick:
        st.dataframe(pd.DataFrame([{"Vehicle": k, "Price/day ₹": names[k]["price_per_day"], "Distance km": names[k]["distance_km"],
            "HP": names[k]["horsepower"], "Rating": names[k]["rating"], "Capacity": names[k]["capacity"], "AI score %": names[k]["score"],
            "Available": "Yes" if names[k]["available"] else "No"} for k in pick]), hide_index=True)
    st.subheader("📅 Book a vehicle")
    sel = st.selectbox("Vehicle", list(names)); v = names[sel]
    hrs = req["duration_hours"]; rent = v["rent_estimate"]; transport = round(v["distance_km"] * 12 / 10) * 10; service = 100
    total = rent + transport + service
    st.write(f"Vehicle rental ₹{rent:,.0f} + Transport ₹{transport:,.0f} + Service charge ₹{service} = **₹{total:,.0f}**  "
             f"(date {req['date']}, {hrs} h, {req['activity']})")
    if st.button("Send booking request", type="primary"):
        if db.is_booked(v["id"], req["date"]): st.error("This vehicle is already booked for the selected date.")
        elif v["availability_status"] != "Available": st.error("This vehicle is not available right now.")
        else:
            db.run("INSERT INTO bookings(farmer_id,vehicle_id,booking_date,duration_value,duration_unit,activity,crop,farm_location,rent,"
                   "transport_charge,service_charge,total_price) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                   (u["id"], v["id"], str(req["date"]), hrs, "hours", req["activity"], req["crop"], ss.loc, rent, transport, service, total))
            db.run("INSERT INTO ai_logs(kind,predicted,actual) VALUES('price',?,?)", (ss.price["expected"], total - transport - service))
            db.notify(v["owner_id"], f"New booking request for {v['brand']} {v['model']} on {req['date']}.")
            st.success("Request sent! Track it under My Bookings.")

def farmer_bookings(u):
    st.header("📅 My Bookings")
    rows = db.q("SELECT b.*, v.brand, v.model, v.owner_id FROM bookings b JOIN vehicles v ON v.id=b.vehicle_id WHERE b.farmer_id=? ORDER BY b.id DESC", (u["id"],))
    if not rows: st.info("No bookings yet."); return
    for b in rows:
        with st.container(border=True):
            st.write(f"**#{b['id']} {b['brand']} {b['model']}** — {b['booking_date']} — ₹{b['total_price']:,.0f} — **{b['status']}**")
            c = st.columns(3)
            if b["status"] == "Accepted" and c[0].button("Confirm booking", key=f"cf{b['id']}"):
                db.run("UPDATE bookings SET status='Confirmed' WHERE id=?", (b["id"],)); db.notify(b["owner_id"], f"Booking #{b['id']} confirmed by farmer."); st.rerun()
            if b["status"] in ("Pending", "Accepted", "Confirmed") and c[1].button("Cancel", key=f"cx{b['id']}"):
                db.run("UPDATE bookings SET status='Cancelled' WHERE id=?", (b["id"],)); db.notify(b["owner_id"], f"Booking #{b['id']} cancelled."); st.rerun()
            if b["status"] in ("Confirmed", "In Progress"):
                v = db.q("SELECT location,latitude,longitude FROM vehicles WHERE id=?", (b["vehicle_id"],), one=True)
                st.caption(f"Vehicle location (shared because of active booking): {v['location']} ({v['latitude']:.3f}, {v['longitude']:.3f})")
            if b["status"] == "Completed" and not db.q("SELECT 1 FROM reviews WHERE booking_id=?", (b["id"],), one=True):
                r = st.slider("Rating", 1, 5, 5, key=f"r{b['id']}"); cm = st.text_input("Comment", key=f"c{b['id']}")
                if st.button("Submit review", key=f"sr{b['id']}"):
                    db.run("INSERT INTO reviews(booking_id,farmer_id,vehicle_id,rating,comment) VALUES(?,?,?,?,?)", (b["id"], u["id"], b["vehicle_id"], r, cm))
                    db.notify(b["owner_id"], f"New {r}★ review received."); st.rerun()

def favorites(u):
    st.header("❤️ Favorites")
    rows = db.q("SELECT v.* FROM favorites f JOIN vehicles v ON v.id=f.vehicle_id WHERE f.user_id=?", (u["id"],))
    st.dataframe(pd.DataFrame(rows)[["brand", "model", "vehicle_type", "horsepower", "price_per_day", "location", "availability_status"]], hide_index=True) if rows else st.info("No favorites yet.")

def notifications(u):
    st.header("🔔 Notifications")
    for n in db.q("SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 30", (u["id"],)): st.write(f"• {n['created_at'][:16]} — {n['message']}")
    db.run("UPDATE notifications SET read_status=1 WHERE user_id=?", (u["id"],))
    with st.expander("Report a problem"):
        m = st.text_area("Describe the problem")
        if st.button("Send complaint") and m.strip(): db.run("INSERT INTO complaints(user_id,message) VALUES(?,?)", (u["id"], m)); st.success("Sent to admin.")

def chat(u):
    st.header("🤖 AgriAssist AI")
    st.caption("Answers come only from live platform data (vehicles, prices, availability). Optional: Ollama can reword answers.")
    use = st.toggle("Use local Ollama to reword (optional)", False)
    ss.setdefault("chat", [])
    for r, m in ss.chat:
        with st.chat_message(r): st.text(m)
    if t := st.chat_input("e.g. I have ₹5000 budget. What can I book?"):
        ss.chat.append(("user", t)); ss.chat.append(("assistant", assistant.answer(t, u, use))); st.rerun()

# ---------------------------------------------------------------- Owner
def owner_vehicles(u):
    st.header("🚜 My Vehicles")
    if u["verification_status"] != "verified": st.warning("Your account is waiting for admin verification. Vehicles are hidden from farmers until then.")
    for v in db.q("SELECT * FROM vehicles WHERE owner_id=?", (u["id"],)):
        with st.container(border=True):
            st.write(f"**{v['brand']} {v['model']}** ({v['vehicle_type']}, {v['horsepower']} HP) — ₹{v['price_per_hour']:.0f}/h, ₹{v['price_per_day']:.0f}/day")
            c = st.columns([2, 2, 1])
            opts = ["Available", "Busy", "Maintenance", "Offline"]
            ns = c[0].selectbox("Status", opts, index=opts.index(v["availability_status"]), key=f"st{v['id']}")
            nl = c[1].selectbox("Current location", list(LOCATIONS), index=list(LOCATIONS).index(v["location"]) if v["location"] in LOCATIONS else 0, key=f"lc{v['id']}")
            if c[2].button("Update", key=f"up{v['id']}"):
                la, lo = LOCATIONS[nl]; db.run("UPDATE vehicles SET availability_status=?,location=?,latitude=?,longitude=? WHERE id=?", (ns, nl, la, lo, v["id"])); st.rerun()
    with st.expander("➕ Add vehicle"):
        types = [t["name"] for t in db.q("SELECT name FROM vehicle_types")] or VEHICLE_TYPES
        c = st.columns(3); t = c[0].selectbox("Type", types); b = c[1].text_input("Brand"); m = c[2].text_input("Model")
        c = st.columns(4); reg = c[0].text_input("Registration no."); hp = c[1].number_input("Horsepower", 0, 500, 45); cap = c[2].text_input("Capacity")
        loc = c[3].selectbox("Location", list(LOCATIONS), key="nl")
        c = st.columns(2); ph = c[0].number_input("Price per hour ₹", 0, 20000, 400); pdy = c[1].number_input("Price per day ₹", 0, 200000, 3000)
        img = st.file_uploader("Vehicle image (optional)", type=["png", "jpg", "jpeg"])
        if st.button("Save vehicle", type="primary"):
            if not b.strip() or not m.strip(): st.error("Brand and model are required.")
            else:
                path = None
                if img:
                    os.makedirs("uploads", exist_ok=True); path = os.path.join("uploads", f"{u['id']}_{img.name}"); open(path, "wb").write(img.getbuffer())
                la, lo = LOCATIONS[loc]
                db.run("INSERT INTO vehicles(owner_id,vehicle_type,brand,model,registration_number,horsepower,capacity,price_per_hour,price_per_day,"
                       "location,latitude,longitude,image) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (u["id"], t, b, m, reg, hp, cap, ph, pdy, loc, la, lo, path)); st.success("Vehicle added."); st.rerun()

def owner_requests(u):
    st.header("📥 Booking Requests")
    rows = db.q("SELECT b.*, v.brand, v.model, f.name fname FROM bookings b JOIN vehicles v ON v.id=b.vehicle_id JOIN users f ON f.id=b.farmer_id "
                "WHERE v.owner_id=? ORDER BY b.id DESC", (u["id"],))
    nxt = {"Pending": [("Accept", "Accepted"), ("Reject", "Rejected")], "Confirmed": [("Start work", "In Progress")], "In Progress": [("Mark completed", "Completed")]}
    for b in rows:
        with st.container(border=True):
            st.write(f"**#{b['id']}** {b['brand']} {b['model']} — {b['fname']} — {b['booking_date']} — {b['activity']} ({b['crop']}) — ₹{b['total_price']:,.0f} — **{b['status']}**")
            for i, (label, new) in enumerate(nxt.get(b["status"], [])):
                if st.button(label, key=f"{label}{b['id']}"):
                    if new == "Accepted" and db.is_booked(b["vehicle_id"], b["booking_date"]): st.error("Date already booked."); continue
                    db.run("UPDATE bookings SET status=? WHERE id=?", (new, b["id"])); db.notify(b["farmer_id"], f"Booking #{b['id']} is now {new}."); st.rerun()

def owner_earnings(u):
    st.header("💵 Earnings")
    r = db.q("SELECT COALESCE(SUM(b.rent+b.transport_charge),0) e, COUNT(*) n FROM bookings b JOIN vehicles v ON v.id=b.vehicle_id WHERE v.owner_id=? AND b.status='Completed'", (u["id"],), one=True)
    c = st.columns(2); c[0].metric("Total earnings", f"₹{r['e']:,.0f}"); c[1].metric("Completed jobs", r["n"])
    st.header("⭐ Reviews")
    for x in db.q("SELECT r.rating,r.comment,v.brand,v.model FROM reviews r JOIN vehicles v ON v.id=r.vehicle_id WHERE v.owner_id=?", (u["id"],)): st.write(f"{'⭐'*x['rating']} {x['brand']} {x['model']} — {x['comment']}")

# ---------------------------------------------------------------- Admin
def admin_dash(u):
    st.header("📊 Admin Dashboard")
    s = lambda sql: db.q(sql, one=True)["n"]
    c = st.columns(4)
    c[0].metric("Farmers", s("SELECT COUNT(*) n FROM users WHERE role='farmer'")); c[1].metric("Owners", s("SELECT COUNT(*) n FROM users WHERE role='owner'"))
    c[2].metric("Vehicles", s("SELECT COUNT(*) n FROM vehicles")); c[3].metric("Bookings", s("SELECT COUNT(*) n FROM bookings"))
    c = st.columns(4)
    rev = s("SELECT COALESCE(SUM(service_charge),0) n FROM bookings WHERE status='Completed'")
    c[0].metric("Platform revenue", f"₹{rev:,.0f}")
    c[1].metric("Active vehicles", s("SELECT COUNT(*) n FROM vehicles WHERE availability_status='Available'"))
    c[2].metric("Pending verification", s("SELECT COUNT(*) n FROM users WHERE role='owner' AND verification_status='pending'")); c[3].metric("Open complaints", s("SELECT COUNT(*) n FROM complaints WHERE status='Open'"))
    t1, t2 = st.tabs(["Popular vehicle types", "Bookings by status"])
    d = pd.DataFrame(db.q("SELECT v.vehicle_type t, COUNT(*) n FROM bookings b JOIN vehicles v ON v.id=b.vehicle_id GROUP BY t"))
    if not d.empty: t1.bar_chart(d.set_index("t"))
    d = pd.DataFrame(db.q("SELECT status s, COUNT(*) n FROM bookings GROUP BY status"))
    if not d.empty: t2.bar_chart(d.set_index("s"))
    d = pd.DataFrame(db.q("SELECT substr(booking_date,1,7) m, COUNT(*) n FROM bookings GROUP BY m"))
    if not d.empty: st.subheader("Monthly bookings"); st.line_chart(d.set_index("m"))

def admin_manage(u):
    st.header("🛠 Manage Platform")
    st.subheader("Verify vehicle owners")
    for o in db.q("SELECT id,name,email,location,verification_status FROM users WHERE role='owner'"):
        c = st.columns([3, 2, 2]); c[0].write(f"{o['name']} ({o['email']})"); c[1].write(o["verification_status"])
        if o["verification_status"] != "verified" and c[2].button("Verify", key=f"vf{o['id']}"):
            db.run("UPDATE users SET verification_status='verified' WHERE id=?", (o["id"],)); db.notify(o["id"], "Your account is verified."); st.rerun()
    st.subheader("Complaints")
    for c_ in db.q("SELECT * FROM complaints ORDER BY id DESC"):
        st.write(f"#{c_['id']} [{c_['status']}] {c_['message']}")
        if c_["status"] == "Open" and st.button("Resolve", key=f"cr{c_['id']}"): db.run("UPDATE complaints SET status='Resolved' WHERE id=?", (c_["id"],)); st.rerun()
    st.subheader("Add vehicle type")
    nt = st.text_input("New vehicle type")
    if st.button("Add type") and nt.strip(): db.run("INSERT OR IGNORE INTO vehicle_types(name) VALUES(?)", (nt.strip(),)); st.success("Added")
    for name, sql in [("Users", "SELECT id,name,email,role,location,verification_status FROM users"), ("Vehicles", "SELECT id,owner_id,vehicle_type,brand,model,price_per_day,availability_status,is_demo FROM vehicles"),
                      ("Bookings", "SELECT id,farmer_id,vehicle_id,booking_date,total_price,status FROM bookings")]:
        with st.expander(name): st.dataframe(pd.DataFrame(db.q(sql)), hide_index=True)

def admin_ai(u):
    st.header("🧠 AI Analytics – Price Prediction Model")
    m = pricing.metrics()
    st.success(f"Best model: **{m['best_model']}**  (train {m['n_train']} / test {m['n_test']} rows)")
    st.dataframe(pd.DataFrame(m["results"]).T.rename(columns={"MAE": "MAE (₹)", "RMSE": "RMSE (₹)", "R2": "R² score"}))
    st.caption(m["note"])
    st.subheader("Feature importance"); st.bar_chart(pd.Series(m["importance"]))
    ap = pd.read_csv(os.path.join(pricing.ML, "actual_vs_predicted.csv")); st.subheader("Actual vs predicted price"); st.scatter_chart(ap, x="actual", y="predicted")
    data = pd.read_csv(os.path.join(os.path.dirname(pricing.ML), "data", "rental_prices.csv"))
    c = st.columns(2)
    c[0].subheader("Average price by vehicle type"); c[0].bar_chart(data.groupby("vehicle_type")["price"].mean())
    c[1].subheader("Average price by location"); c[1].bar_chart(data.groupby("location")["price"].mean())
    st.subheader("Demand by month"); st.line_chart(data.groupby("month")["demand"].mean())
    st.subheader("Recommendation weights (edit core/recommend.py → WEIGHTS)"); st.json(recommend.WEIGHTS)

# ---------------------------------------------------------------- Router
def main():
    u = ss.user
    if not u: landing(); return
    unread = db.q("SELECT COUNT(*) n FROM notifications WHERE user_id=? AND read_status=0", (u["id"],), one=True)["n"]
    st.sidebar.title("🚜 AgriConnect AI"); st.sidebar.write(f"👤 {u['name']} ({u['role']})")
    pages = {"farmer": {"🔎 Find Vehicles": farmer_find, "📅 My Bookings": farmer_bookings, "❤️ Favorites": favorites, f"🔔 Notifications ({unread})": notifications, "🤖 AgriAssist": chat},
             "owner": {"🚜 My Vehicles": owner_vehicles, "📥 Booking Requests": owner_requests, "💵 Earnings & Reviews": owner_earnings, f"🔔 Notifications ({unread})": notifications},
             "admin": {"📊 Dashboard": admin_dash, "🛠 Manage": admin_manage, "🧠 AI Analytics": admin_ai}}[u["role"]]
    page = st.sidebar.radio("Menu", list(pages)); pages[page](u)
    st.sidebar.button("Logout", on_click=logout)
    st.sidebar.caption("Demo/sample data is labelled. AI price model trained on simulated rental data.")
main()
