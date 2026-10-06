"""Create demo data. All records are SAMPLE data. Run: python seed.py"""
import os, random
from core import db, auth
from core.constants import LOCATIONS, VEHICLE_TYPES
if os.path.exists(db.DB_PATH): os.remove(db.DB_PATH)
db.init_db()
for t in VEHICLE_TYPES: db.run("INSERT OR IGNORE INTO vehicle_types(name) VALUES(?)", (t,))
def user(n, e, r, loc, ph="9000000000", st="verified"):
    uid, _ = auth.register(n, ph, e, "Demo@123", r, loc, *LOCATIONS[loc])
    db.run("UPDATE users SET verification_status=? WHERE id=?", (st, uid)); return uid
farmer = user("Demo Farmer", "farmer@demo.com", "farmer", "Guntur")
owner = user("Demo Vehicle Owner", "owner@demo.com", "owner", "Guntur")
owner2 = user("Ramesh Reddy (Sample)", "owner2@demo.com", "owner", "Vijayawada")
owner3 = user("Lakshmi Agro (Sample)", "owner3@demo.com", "owner", "Tenali", st="pending")
user("Demo Admin", "admin@demo.com", "admin", "Hyderabad")
V = [(owner, "Tractor", "Mahindra", "575 DI", 50, "2 ton", 400, 3000, "Guntur"),
     (owner, "Tractor", "John Deere", "5050 D", 50, "2 ton", 450, 3400, "Narasaraopet"),
     (owner, "Rotavator", "Shaktiman", "Regular 6ft", 40, "6 ft", 450, 3200, "Tenali"),
     (owner2, "Tractor", "Swaraj", "744 FE", 48, "2 ton", 380, 2800, "Vijayawada"),
     (owner2, "Combine Harvester", "Kubota", "DC-68G", 68, "Paddy", 2200, 16000, "Vijayawada"),
     (owner2, "Cultivator", "Fieldking", "9-Tyne", 35, "9 tyne", 300, 2200, "Eluru"),
     (owner, "Combine Harvester", "Preet", "987", 75, "Multi-crop", 2000, 15000, "Guntur"),
     (owner2, "Sprayer", "Neptune", "Boom 400L", 30, "400 L", 320, 2400, "Tenali"),
     (owner, "Seed Drill", "Kartar", "9-Row", 40, "9 row", 380, 2800, "Ongole"),
     (owner2, "Tractor", "Sonalika", "DI 750", 55, "2.5 ton", 420, 3100, "Machilipatnam"),
     (owner, "Thresher", "Dashmesh", "Multicrop", 40, "Multi", 600, 4500, "Guntur"),
     (owner3, "Trailer", "Sample", "Tipping 3T", 40, "3 ton", 260, 1900, "Narasaraopet")]
random.seed(1)
for o, t, b, m, hp, cap, ph, pd_, loc in V:
    la, lo = LOCATIONS[loc]
    db.run("INSERT INTO vehicles(owner_id,vehicle_type,brand,model,registration_number,horsepower,capacity,price_per_hour,price_per_day,"
           "location,latitude,longitude,availability_status,is_demo) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,1)",
           (o, t, b, m, f"AP-{random.randint(10,39)}-AB-{random.randint(1000,9999)}", hp, cap, ph, pd_, loc,
            la + random.uniform(-.03, .03), lo + random.uniform(-.03, .03), "Busy" if (b == "Sonalika") else "Available"))
for i, (vid, r, c) in enumerate([(1, 5, "Very punctual, good tractor."), (1, 4, "Good work."), (2, 5, "Excellent."),
                                  (4, 4, "Fair price."), (5, 5, "Fast harvesting."), (5, 4, "Good machine.")]):
    bid = db.run("INSERT INTO bookings(farmer_id,vehicle_id,booking_date,duration_value,duration_unit,activity,crop,farm_location,rent,"
                 "transport_charge,service_charge,total_price,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,'Completed')",
                 (farmer, vid, f"2026-09-{10+i:02d}", 1, "days", "Ploughing", "Paddy", "Guntur", 3000, 200, 100, 3300))
    db.run("INSERT INTO reviews(booking_id,farmer_id,vehicle_id,rating,comment) VALUES(?,?,?,?,?)", (bid, farmer, vid, r, c))
print("Demo data ready. Logins: farmer@demo.com / owner@demo.com / admin@demo.com  (password: Demo@123)")
