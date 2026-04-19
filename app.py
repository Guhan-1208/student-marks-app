import os
import datetime
import logging
from functools import wraps

import bcrypt
import jwt
import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError
from werkzeug.utils import secure_filename

# ================= CONFIG =================

JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET environment variable must be set")

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/student_marks_db")
DB_NAME   = os.environ.get("DB_NAME", "student_marks_db")
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "uploads")
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "10"))
JWT_EXP_HOURS = int(os.environ.get("JWT_EXP_HOURS", "6"))
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "").split(",") if os.environ.get("CORS_ORIGINS") else []

ALLOWED_EXTS = {".xlsx", ".xls", ".csv"}

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024
CORS(app, origins=CORS_ORIGINS or "*")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("student-marks-api")

# ================= DB =================

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
    db = client[DB_NAME]
    logger.info(f"Connected to MongoDB: {DB_NAME}")
except Exception as e:
    logger.error(f"MongoDB connection error: {e}")
    raise

students_col = db.students
marks_col = db.marks
staff_col = db.staff
uploads_col = db.uploads

try:
    students_col.create_index([("register_number", ASCENDING)], unique=True)
    staff_col.create_index([("email", ASCENDING)], unique=True)
    marks_col.create_index(
        [("register_number", ASCENDING), ("subject_code", ASCENDING)],
        unique=True
    )
except Exception as e:
    logger.warning(f"Index creation warning: {e}")

# ================= HELPERS =================

def hash_text(text: str) -> str:
    return bcrypt.hashpw(text.encode(), bcrypt.gensalt()).decode()

def verify_hash(text: str, hashed: str) -> bool:
    return bool(hashed) and bcrypt.checkpw(text.encode(), hashed.encode())

def generate_jwt(payload: dict) -> str:
    payload = payload.copy()
    payload["exp"] = datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXP_HOURS)
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def decode_jwt(token: str):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return {"_error": "expired"}
    except jwt.InvalidTokenError:
        return {"_error": "invalid"}

def require_auth(role=None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Bearer "):
                return jsonify({"error": "Missing token"}), 401
            token = auth.replace("Bearer ", "", 1).strip()
            data = decode_jwt(token)
            if not data or data.get("_error"):
                return jsonify({"error": "Invalid or expired token"}), 401
            if role and data.get("role") != role:
                return jsonify({"error": "Forbidden"}), 403
            request.user = data
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def allowed_file(name: str) -> bool:
    _, ext = os.path.splitext(name.lower())
    return ext in ALLOWED_EXTS

# ================= HEALTH =================

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "time": datetime.datetime.utcnow().isoformat()})

# ================= AUTH =================

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(force=True, silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    user = staff_col.find_one({"email": email})
    if not user or not verify_hash(password, user.get("password_hash", "")):
        return jsonify({"error": "Invalid credentials"}), 401

    token = generate_jwt({"email": email, "role": user.get("role", "staff")})
    return jsonify({"token": token})

# ================= UPLOAD MARKS =================

@app.route("/api/upload-marks", methods=["POST"])
@require_auth()
def upload_marks():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Unsupported file type"}), 400

    filename = secure_filename(file.filename)
    path = os.path.join(UPLOAD_DIR, filename)
    file.save(path)

    try:
        if filename.lower().endswith(".csv"):
            df = pd.read_csv(path, dtype=str, keep_default_na=False)
        else:
            df = pd.read_excel(path, dtype=str, keep_default_na=False, engine="openpyxl")
        df = df.copy()
        import gc; gc.collect()
    except Exception:
        logger.exception("Failed reading file")
        return jsonify({"error": "Invalid spreadsheet"}), 400

    df.columns = [c.lower().strip() for c in df.columns]
    required = {"register_number", "subject_code", "marks"}
    if not required.issubset(set(df.columns)):
        return jsonify({"error": "Missing required columns"}), 400

    from pymongo import UpdateOne

    student_ops = []
    marks_ops = []
    now = datetime.datetime.utcnow()

    for _, row in df.iterrows():
        reg     = str(row.get("register_number", "")).strip()
        subject = str(row.get("subject_code", "")).strip()
        marks_val = row.get("marks", "")

        if not reg or not subject or marks_val == "" or marks_val is None:
            continue
        try:
            marks_val = float(marks_val)
        except (ValueError, TypeError):
            continue

        student_name = row.get("student_name", "").strip() or None
        dob = None
        raw_dob = row.get("dob", "").strip()
        if raw_dob:
            try:
                dob = pd.to_datetime(raw_dob).date().isoformat()
            except Exception:
                dob = None

        set_fields = {}
        if student_name:
            set_fields["student_name"] = student_name

        set_on_insert = {"register_number": reg, "created_at": now}
        if dob:
            set_on_insert["dob_hash"] = hash_text(dob)

        student_ops.append(UpdateOne(
            {"register_number": reg},
            {"$set": set_fields, "$setOnInsert": set_on_insert},
            upsert=True
        ))

        marks_ops.append(UpdateOne(
            {"register_number": reg, "subject_code": subject},
            {"$set": {
                "marks": marks_val,
                "uploaded_by": request.user["email"],
                "uploaded_at": now,
                "source_file": filename
            }},
            upsert=True
        ))

    if not marks_ops:
        return jsonify({"error": "No valid rows found in file"}), 400

    # Single bulk write for students, single bulk write for marks
    if student_ops:
        students_col.bulk_write(student_ops, ordered=False)
    result = marks_col.bulk_write(marks_ops, ordered=False)
    inserted = result.upserted_count + result.modified_count

    uploads_col.insert_one({
        "filename": filename,
        "uploaded_by": request.user["email"],
        "uploaded_at": now
    })

    return jsonify({"status": "success", "processed": inserted})

# ================= STUDENT LOOKUP =================

@app.route("/api/students/lookup", methods=["POST"])
def lookup():
    data = request.get_json(force=True, silent=True) or {}
    reg = str(data.get("register_number", "")).strip()
    dob = str(data.get("dob", "")).strip()

    if not reg or not dob:
        return jsonify({"error": "register_number and dob required"}), 400

    student = students_col.find_one({"register_number": reg})
    if not student or not verify_hash(dob, student.get("dob_hash", "")):
        return jsonify({"error": "Invalid details"}), 401

    marks = list(marks_col.find(
        {"register_number": reg},
        {"_id": 0}
    ))

    return jsonify({
        "register_number": reg,
        "student_name": student.get("student_name"),
        "marks": marks
    })

# ================= ADMIN =================

@app.route("/api/admin/uploads", methods=["GET"])
@require_auth("admin")
def list_uploads():
    files = []
    for u in uploads_col.find():
        p = os.path.join(UPLOAD_DIR, u["filename"])
        if os.path.exists(p):
            files.append({
                "name": u["filename"],
                "size_bytes": os.path.getsize(p),
                "modified_at": os.path.getmtime(p)
            })
    return jsonify({"uploads": files})

@app.route("/api/admin/uploads", methods=["DELETE"])
@require_auth("admin")
def delete_upload():
    data = request.get_json(force=True, silent=True) or {}
    name = secure_filename(data.get("filename", ""))

    if not name:
        return jsonify({"error": "filename required"}), 400

    path = os.path.join(UPLOAD_DIR, name)
    if os.path.exists(path):
        os.remove(path)

    uploads_col.delete_one({"filename": name})

    # ✅ ALSO delete marks imported from this file
    marks_col.delete_many({"source_file": name})

    return jsonify({"status": "deleted"})

# ================= MAIN =================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)