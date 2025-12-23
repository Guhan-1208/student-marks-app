#!/usr/bin/env python3
"""
Migration / init helper for MongoDB.

Features:
- create required indexes
- seed an admin staff user (prints the password)
- import marks from an Excel (.xlsx/.xls) or CSV file into the collections:
    students, marks, staff

Run with:
    python migrate_to_mongo.py --seed-admin
    python migrate_to_mongo.py --import-file /path/to/marks.xlsx
"""

import os
import sys
import argparse
import getpass
import datetime
import bcrypt
import pandas as pd
from pymongo import MongoClient, errors

# ---------------------------
# Config (can be overridden by env var)
# ---------------------------
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/student_marks_db")
DB_NAME = os.getenv("DB_NAME", "student_marks_db")

# Default admin creds (change for production)
DEFAULT_ADMIN_EMAIL = "admin@example.com"
DEFAULT_ADMIN_PASSWORD = "admin123"

# ---------------------------
# Helpers
# ---------------------------

def get_db(uri=MONGO_URI, name=DB_NAME):
    client = MongoClient(uri)
    return client[name]


def create_indexes(db):
    print("Creating indexes...")
    db.students.create_index("register_number", unique=True)
    db.staff.create_index("email", unique=True)
    db.marks.create_index("register_number")
    print("Indexes ensured.")


def create_admin_if_missing(db, email=DEFAULT_ADMIN_EMAIL, password=None):
    staff = db.staff
    existing = staff.find_one({"email": email})
    if existing:
        print(f"Admin user already exists: {email}")
        return None

    if not password:
        # for scripts it's ok to use default; interactive prompt available
        password = DEFAULT_ADMIN_PASSWORD

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    staff.insert_one({
        "email": email,
        "password_hash": hashed.decode(),
        "role": "admin",
        "created_at": datetime.datetime.utcnow()
    })
    print("Admin user created:")
    print("  email: ", email)
    print("  password: ", password)
    return {"email": email, "password": password}


def normalize_columns(cols):
    """
    Lowercase & strip column names for easier matching.
    Returns a mapping from lower->original.
    """
    mapping = {}
    for c in cols:
        mapping[c.lower().strip()] = c
    return mapping


def import_marks_file(db, filepath, sheet_name=None):
    """
    Reads spreadsheet (xlsx/xls) or csv and inserts rows into students & marks collections.
    Expected columns (case-insensitive):
      - register_number (required)
      - subject_code (required)
      - marks (required)
    Optional:
      - student_name
      - dob (YYYY-MM-DD or other parseable date)
      - subject_name
      - exam_date
    """
    print("Importing file:", filepath)
    if not os.path.exists(filepath):
        print("File not found:", filepath)
        return {"error": "file-not-found"}

    _, ext = os.path.splitext(filepath.lower())
    try:
        if ext in (".xlsx", ".xls"):
            df = pd.read_excel(filepath, sheet_name=sheet_name)
        elif ext == ".csv":
            df = pd.read_csv(filepath)
        else:
            print("Unsupported file extension:", ext)
            return {"error": "unsupported-extension"}
    except Exception as e:
        print("Error reading file:", e)
        return {"error": "read-error", "detail": str(e)}

    if df.empty:
        print("No rows found in file.")
        return {"inserted": 0, "errors": ["empty file"]}

    colmap = normalize_columns(df.columns)
    req = ["register_number", "subject_code", "marks"]
    for r in req:
        if r not in colmap:
            print(f"Missing required column: {r}")
            return {"error": "missing-column", "missing": r}

    inserted = 0
    errors = []
    students_col = db.students
    marks_col = db.marks

    for idx, row in df.iterrows():
        try:
            # access original column names via mapping
            reg = str(row[colmap["register_number"]]).strip()
            subject = str(row[colmap["subject_code"]]).strip()
            marks_val = row[colmap["marks"]]

            if pd.isna(reg) or reg == "" or pd.isna(subject) or pd.isna(marks_val):
                errors.append({"row": int(idx)+2, "error": "missing required"})
                continue

            # optional fields
            dob = None
            if "dob" in colmap:
                raw_dob = row[colmap["dob"]]
                if not pd.isna(raw_dob):
                    # try parse via pandas
                    try:
                        dob_parsed = pd.to_datetime(raw_dob).date().isoformat()
                        dob = dob_parsed
                    except Exception:
                        dob = str(raw_dob).strip()

            student_name = None
            if "student_name" in colmap:
                val = row[colmap["student_name"]]
                if not pd.isna(val):
                    student_name = str(val).strip()

            subject_name = None
            if "subject_name" in colmap:
                val = row[colmap["subject_name"]]
                if not pd.isna(val):
                    subject_name = str(val).strip()

            exam_date = None
            if "exam_date" in colmap:
                val = row[colmap["exam_date"]]
                if not pd.isna(val):
                    try:
                        exam_date = pd.to_datetime(val).date().isoformat()
                    except Exception:
                        exam_date = str(val).strip()

            # upsert student (do not overwrite dob_hash if already present)
            existing = students_col.find_one({"register_number": reg})
            if not existing:
                dob_hash = bcrypt.hashpw(dob.encode(), bcrypt.gensalt()).decode() if dob else None
                students_col.insert_one({
                    "register_number": reg,
                    "student_name": student_name,
                    "dob_hash": dob_hash,
                    "created_at": datetime.datetime.utcnow()
                })
            else:
                # if student exists but dob provided and dob_hash missing, set it
                if dob and not existing.get("dob_hash"):
                    dob_hash = bcrypt.hashpw(dob.encode(), bcrypt.gensalt()).decode()
                    students_col.update_one(
                        {"register_number": reg},
                        {"$set": {"dob_hash": dob_hash, "student_name": student_name}}
                    )

            # insert mark
            marks_col.insert_one({
                "register_number": reg,
                "subject_code": subject,
                "subject_name": subject_name,
                "marks": float(marks_val),
                "exam_date": exam_date,
                "uploaded_by": "migration-script",
                "uploaded_at": datetime.datetime.utcnow()
            })

            inserted += 1

        except Exception as e:
            errors.append({"row": int(idx)+2, "error": str(e)})
            continue

    print(f"Import finished. Inserted: {inserted}, Errors: {len(errors)}")
    return {"inserted": inserted, "errors": errors}


# ---------------------------
# CLI
# ---------------------------

def main():
    parser = argparse.ArgumentParser(description="MongoDB migration & import helper")
    parser.add_argument("--seed-admin", action="store_true", help="Create admin user if missing")
    parser.add_argument("--admin-email", type=str, default=DEFAULT_ADMIN_EMAIL, help="Admin email")
    parser.add_argument("--admin-password", type=str, default=None, help="Admin password (if omitted will use default or prompt)")
    parser.add_argument("--import-file", type=str, help="Path to Excel or CSV file to import")
    parser.add_argument("--sheet", type=str, default=None, help="Sheet name (for Excel import)")
    parser.add_argument("--mongo-uri", type=str, default=MONGO_URI, help="MongoDB connection URI")
    args = parser.parse_args()

    print("Connecting to MongoDB:", args.mongo_uri)
global MONGO_URI, DB_NAME
MONGO_URI = args.mongo_uri

try:
    client = MongoClient(MONGO_URI)

        db = client[DB_NAME]
    except errors.PyMongoError as e:
        print("Failed to connect to MongoDB:", e)
        sys.exit(1)

    # create indexes
    try:
        create_indexes(db)
    except Exception as e:
        print("Error creating indexes:", e)

    # seed admin
    if args.seed_admin:
        pw = args.admin_password
        if (not pw):
            # try interactive prompt (but avoid echoing if containerized)
            try:
                pw = getpass.getpass("Enter admin password (leave empty to use default): ")
                if not pw:
                    pw = DEFAULT_ADMIN_PASSWORD
            except Exception:
                pw = DEFAULT_ADMIN_PASSWORD
        create_admin_if_missing(db, email=args.admin_email, password=pw)

    # import file if requested
    if args.import_file:
        result = import_marks_file(db, args.import_file, sheet_name=args.sheet)
        print("Import result:", result)

    print("Done.")


if __name__ == "__main__":
    main()
