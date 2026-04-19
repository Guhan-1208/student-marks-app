"""
Run once to create your admin account:
  python seed_admin.py
Set MONGO_URI and JWT_SECRET env vars first.
"""
import os, bcrypt
from pymongo import MongoClient

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/student_marks_db")
client = MongoClient(MONGO_URI)
db = client.get_default_database()

email    = input("Admin email: ").strip().lower()
password = input("Admin password: ").strip()
name     = input("Your name (optional): ").strip()

hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
db.staff.update_one(
    {"email": email},
    {"$set": {"email": email, "password_hash": hashed, "role": "admin", "name": name}},
    upsert=True
)
print(f"✓ Admin created: {email}")
