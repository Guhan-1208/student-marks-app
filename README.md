# Student Marks Portal

A web app where staff upload student marks (Excel/CSV) and students look up their results using their register number + date of birth.

## Stack
- **Frontend**: Single HTML file → Netlify
- **Backend**: Python Flask + MongoDB Atlas → Render
- **Database**: MongoDB Atlas (free tier)

---

## Quick Deploy

### Step 1 — MongoDB Atlas (free)
1. Go to mongodb.com/atlas → Create free cluster
2. Create a database user (username + password)
3. Whitelist all IPs: `0.0.0.0/0`
4. Get connection string → looks like:
   `mongodb+srv://user:password@cluster.mongodb.net/student_marks_db`

### Step 2 — Create Admin Account
```bash
pip install pymongo[srv] bcrypt
MONGO_URI="your_atlas_uri" python seed_admin.py
```

### Step 3 — Deploy Backend to Render
1. Push this folder to GitHub
2. Render → New Web Service → connect repo
3. Build: `pip install -r requirements.txt`
4. Start: `gunicorn app:app --bind 0.0.0.0:$PORT`
5. Environment variables:
   ```
   MONGO_URI     = mongodb+srv://...
   JWT_SECRET    = any_long_random_string
   CORS_ORIGINS  = https://your-site.netlify.app
   ```
6. Copy your Render URL e.g. `https://marks-api.onrender.com`

### Step 4 — Deploy Frontend to Netlify
1. Open `index.html`, find line:
   ```js
   : 'https://YOUR-BACKEND.onrender.com/api';
   ```
   Replace with your Render URL.
2. Drag & drop `index.html` to netlify.com/drop

---

## Excel/CSV Format

Your upload file must have these columns:

| register_number | subject_code | marks | student_name | dob        |
|----------------|--------------|-------|--------------|------------|
| 421622205001   | CS301        | 87    | Ananya S     | 2003-08-12 |
| 421622205001   | MA201        | 92    | Ananya S     | 2003-08-12 |
| 421622205002   | CS301        | 74    | Ravi K       | 2004-01-05 |

- `register_number`, `subject_code`, `marks` are required
- `student_name` and `dob` are optional but needed for student lookup
- `dob` format: YYYY-MM-DD

## Student Lookup
Students enter their register number + date of birth (DD-MM-YYYY) to view marks. DOB is hashed in the database for privacy.
