import datetime
import bcrypt
from pymongo.collection import Collection


# -----------------------------------------------------
# HASHING HELPERS
# -----------------------------------------------------

def hash_text(text: str) -> str:
    """Return bcrypt hash for any text (password or DOB)."""
    return bcrypt.hashpw(text.encode(), bcrypt.gensalt()).decode()


def verify_hash(text: str, hashed: str) -> bool:
    """Check whether text matches a bcrypt hash."""
    if not hashed:
        return False
    return bcrypt.checkpw(text.encode(), hashed.encode())


# -----------------------------------------------------
# STUDENT HELPERS
# -----------------------------------------------------

def upsert_student(students_col: Collection, register_number: str, dob: str = None):
    """
    Insert or update a student record.
    If the student exists and dob is provided, we do NOT overwrite it.
    """
    existing = students_col.find_one({"register_number": register_number})

    if existing:
        # Don't overwrite dob_hash if already set unless dob is explicitly given
        if dob:
            dob_hash = hash_text(dob)
            students_col.update_one(
                {"register_number": register_number},
                {"$set": {"dob_hash": dob_hash}}
            )
        return existing["_id"]

    # Insert new student
    dob_hash = hash_text(dob) if dob else None

    result = students_col.insert_one({
        "register_number": register_number,
        "dob_hash": dob_hash,
        "created_at": datetime.datetime.utcnow()
    })

    return result.inserted_id


# -----------------------------------------------------
# STAFF HELPERS
# -----------------------------------------------------

def create_staff_user(staff_col: Collection, email: str, password: str, role="staff"):
    """
    Create a staff user.
    Used mainly during initial seeding.
    """
    existing = staff_col.find_one({"email": email})
    if existing:
        return existing["_id"]

    password_hash = hash_text(password)

    result = staff_col.insert_one({
        "email": email,
        "password_hash": password_hash,
        "role": role,
        "created_at": datetime.datetime.utcnow()
    })

    return result.inserted_id


# -----------------------------------------------------
# MARKS HELPERS
# -----------------------------------------------------

def insert_mark(marks_col: Collection, register_number: str, subject: str, marks: float, uploaded_by: str):
    """
    Insert a single marks entry for a student.
    """
    marks_col.insert_one({
        "register_number": register_number,
        "subject_code": subject,
        "marks": marks,
        "uploaded_by": uploaded_by,
        "uploaded_at": datetime.datetime.utcnow()
    })


def get_marks_for_student(marks_col: Collection, register_number: str):
    """
    Get all marks for a student.
    """
    return list(
        marks_col.find(
            {"register_number": register_number},
            {"_id": 0}
        )
    )
