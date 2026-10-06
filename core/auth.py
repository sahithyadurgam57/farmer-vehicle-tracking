import hashlib, hmac, os
from core import db
def hash_password(pw: str) -> str:
    salt = os.urandom(16); h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000)
    return salt.hex() + "$" + h.hex()
def verify_password(pw: str, stored: str) -> bool:
    salt, h = stored.split("$"); new = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 200_000)
    return hmac.compare_digest(new.hex(), h)
def register(name, phone, email, password, role, location, lat, lon):
    email = email.strip().lower()
    if len(password) < 6: return None, "Password must be at least 6 characters."
    if "@" not in email: return None, "Please enter a valid email."
    if db.q("SELECT 1 FROM users WHERE email=?", (email,), one=True): return None, "This email is already registered."
    status = "pending" if role == "owner" else "verified"
    uid = db.run("INSERT INTO users(name,phone,email,password_hash,role,location,latitude,longitude,verification_status)"
                 " VALUES(?,?,?,?,?,?,?,?,?)", (name, phone, email, hash_password(password), role, location, lat, lon, status))
    return uid, None
def login(email, password):
    u = db.q("SELECT * FROM users WHERE email=?", (email.strip().lower(),), one=True)
    if u and verify_password(password, u["password_hash"]):
        u.pop("password_hash"); return u
    return None
