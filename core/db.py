"""SQLite database layer (plain SQL, easy to migrate to PostgreSQL later)."""
import sqlite3, os
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agriconnect.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT,
  email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN('farmer','owner','admin')),
  location TEXT, latitude REAL, longitude REAL, verification_status TEXT DEFAULT 'verified',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS vehicles(id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER NOT NULL REFERENCES users(id),
  vehicle_type TEXT, brand TEXT, model TEXT, registration_number TEXT, horsepower INTEGER, capacity TEXT,
  price_per_hour REAL, price_per_day REAL, location TEXT, latitude REAL, longitude REAL,
  availability_status TEXT DEFAULT 'Available', image TEXT, is_demo INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS bookings(id INTEGER PRIMARY KEY AUTOINCREMENT, farmer_id INTEGER REFERENCES users(id),
  vehicle_id INTEGER REFERENCES vehicles(id), booking_date TEXT, duration_value INTEGER, duration_unit TEXT,
  activity TEXT, crop TEXT, farm_location TEXT, rent REAL, transport_charge REAL, service_charge REAL,
  total_price REAL, status TEXT DEFAULT 'Pending', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS reviews(id INTEGER PRIMARY KEY AUTOINCREMENT, booking_id INTEGER UNIQUE, farmer_id INTEGER,
  vehicle_id INTEGER, rating INTEGER, comment TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS notifications(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message TEXT,
  read_status INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS favorites(user_id INTEGER, vehicle_id INTEGER, PRIMARY KEY(user_id, vehicle_id));
CREATE TABLE IF NOT EXISTS complaints(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message TEXT,
  status TEXT DEFAULT 'Open', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS vehicle_types(name TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS ai_logs(id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, predicted REAL, actual REAL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP);
"""

def conn():
    c = sqlite3.connect(DB_PATH); c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON"); return c

def init_db():
    with conn() as c: c.executescript(SCHEMA)

def q(sql, params=(), one=False):
    with conn() as c:
        rows = [dict(r) for r in c.execute(sql, params).fetchall()]
    return (rows[0] if rows else None) if one else rows

def run(sql, params=()):
    with conn() as c:
        cur = c.execute(sql, params); return cur.lastrowid

def notify(user_id, message):
    run("INSERT INTO notifications(user_id,message) VALUES(?,?)", (user_id, message))

def vehicle_rating(vehicle_id):
    r = q("SELECT AVG(rating) a, COUNT(*) n FROM reviews WHERE vehicle_id=?", (vehicle_id,), one=True)
    return (round(r["a"], 1) if r["a"] else 0.0), r["n"]

def is_booked(vehicle_id, date):
    return bool(q("SELECT 1 FROM bookings WHERE vehicle_id=? AND booking_date=? AND status IN "
                  "('Accepted','Confirmed','In Progress')", (vehicle_id, str(date)), one=True))
