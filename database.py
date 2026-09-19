import sqlite3
import hashlib
import json
from datetime import datetime


# =========================================================
# DATABASE CONFIGURATION
# =========================================================

DB_NAME = "interview.db"


# =========================================================
# CONNECTION
# =========================================================

def get_connection():
    return sqlite3.connect(DB_NAME)


# =========================================================
# PASSWORD HASHING
# =========================================================

def hash_password(password):
    return hashlib.sha256(
        password.encode("utf-8")
    ).hexdigest()


# =========================================================
# CREATE / UPDATE DATABASE
# =========================================================

def create_database():

    conn = get_connection()
    cursor = conn.cursor()

    # =====================================================
    # USERS TABLE
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # Check old users table columns
    cursor.execute("PRAGMA table_info(users)")
    user_columns = [row[1] for row in cursor.fetchall()]

    # Add name to old database if missing
    if "name" not in user_columns:
        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN name TEXT
        """)

    # =====================================================
    # PROFILES TABLE
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT,
            target_role TEXT,
            education TEXT,
            bio TEXT
        )
    """)

    # =====================================================
    # INTERVIEWS TABLE
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            job_role TEXT,
            field TEXT,
            experience TEXT,
            interview_type TEXT,
            difficulty TEXT,
            question TEXT,
            answer TEXT,
            score REAL,
            feedback TEXT,
            created_at TEXT
        )
    """)

    # Check old interviews table
    cursor.execute("PRAGMA table_info(interviews)")
    interview_columns = [row[1] for row in cursor.fetchall()]

    # Add user_id if old database doesn't have it
    if "user_id" not in interview_columns:
        cursor.execute("""
            ALTER TABLE interviews
            ADD COLUMN user_id INTEGER
        """)

    # =====================================================
    # PERSISTENT INTERVIEW SESSIONS
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interview_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            job_role TEXT,
            field TEXT,
            experience TEXT,
            interview_type TEXT,
            difficulty TEXT,
            number_questions INTEGER,
            current_question INTEGER,
            question TEXT,
            answer TEXT,
            answer_submitted INTEGER,
            feedback TEXT,
            scores TEXT,
            resume_text TEXT,
            updated_at TEXT
        )
    """)

    conn.commit()
    conn.close()


# =========================================================
# CREATE USER
# =========================================================

def create_user(name, email, password):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        name = name.strip()
        email = email.strip().lower()

        if not name:
            return False, "Please enter your name."

        if not email:
            return False, "Please enter your email."

        if not password:
            return False, "Please enter a password."

        hashed_password = hash_password(password)

        cursor.execute("""
            INSERT INTO users (
                name,
                email,
                password
            )
            VALUES (?, ?, ?)
        """, (
            name,
            email,
            hashed_password
        ))

        user_id = cursor.lastrowid

        # Create profile automatically
        cursor.execute("""
            INSERT OR IGNORE INTO profiles (
                user_id,
                name,
                email
            )
            VALUES (?, ?, ?)
        """, (
            user_id,
            name,
            email
        ))

        conn.commit()

        return True, "Account created successfully."

    except sqlite3.IntegrityError:

        return False, "An account with this email already exists."

    except Exception as e:

        return False, f"Could not create account: {e}"

    finally:

        conn.close()


# =========================================================
# LOGIN USER
# =========================================================

def login_user(email, password):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        email = email.strip().lower()
        hashed_password = hash_password(password)

        cursor.execute("""
            SELECT
                id,
                name,
                email
            FROM users
            WHERE email = ?
            AND password = ?
        """, (
            email,
            hashed_password
        ))

        user = cursor.fetchone()

        if user:

            return {
                "id": user[0],
                "name": user[1] or "",
                "email": user[2]
            }

        return None

    finally:

        conn.close()


# =========================================================
# GET USER NAME
# =========================================================

def get_user_name(user_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name
        FROM users
        WHERE id = ?
    """, (user_id,))

    result = cursor.fetchone()

    conn.close()

    if result:
        return result[0] or ""

    return ""


# =========================================================
# SAVE PROFILE
# =========================================================

def save_profile(
    user_id,
    name,
    email,
    target_role,
    education,
    bio
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO profiles (
            user_id,
            name,
            email,
            target_role,
            education,
            bio
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        name,
        email,
        target_role,
        education,
        bio
    ))

    # Update name in users table too
    cursor.execute("""
        UPDATE users
        SET name = ?
        WHERE id = ?
    """, (
        name,
        user_id
    ))

    conn.commit()
    conn.close()


# =========================================================
# GET PROFILE
# =========================================================

def get_profile(user_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            name,
            email,
            target_role,
            education,
            bio
        FROM profiles
        WHERE user_id = ?
    """, (user_id,))

    profile = cursor.fetchone()

    conn.close()

    return profile


# =========================================================
# SAVE INTERVIEW
# =========================================================

def save_interview(
    user_id,
    job_role,
    field,
    experience,
    interview_type,
    difficulty,
    question,
    answer,
    score,
    feedback
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO interviews (
            user_id,
            job_role,
            field,
            experience,
            interview_type,
            difficulty,
            question,
            answer,
            score,
            feedback,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        job_role,
        field,
        experience,
        interview_type,
        difficulty,
        question,
        answer,
        score,
        feedback,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


# =========================================================
# GET USER INTERVIEWS
# =========================================================

def get_interviews(user_id=None):

    conn = get_connection()
    cursor = conn.cursor()

    if user_id is not None:

        cursor.execute("""
            SELECT
                id,
                job_role,
                field,
                experience,
                interview_type,
                difficulty,
                question,
                answer,
                score,
                feedback,
                created_at
            FROM interviews
            WHERE user_id = ?
            ORDER BY id DESC
        """, (user_id,))

    else:

        cursor.execute("""
            SELECT
                id,
                job_role,
                field,
                experience,
                interview_type,
                difficulty,
                question,
                answer,
                score,
                feedback,
                created_at
            FROM interviews
            ORDER BY id DESC
        """)

    data = cursor.fetchall()

    conn.close()

    return data


# =========================================================
# SAVE PERSISTENT INTERVIEW SESSION
# =========================================================

def save_session(
    user_id,
    job_role,
    field,
    experience,
    interview_type,
    difficulty,
    number_questions,
    current_question,
    question,
    answer,
    answer_submitted,
    feedback,
    scores,
    resume_text
):

    conn = get_connection()
    cursor = conn.cursor()

    feedback_json = ""

    if feedback:
        try:
            feedback_json = json.dumps(feedback)
        except Exception:
            feedback_json = str(feedback)

    scores_json = json.dumps(scores)

    # Check if session already exists
    cursor.execute("""
        SELECT id
        FROM interview_sessions
        WHERE user_id = ?
    """, (user_id,))

    existing = cursor.fetchone()

    if existing:

        cursor.execute("""
            UPDATE interview_sessions
            SET
                job_role = ?,
                field = ?,
                experience = ?,
                interview_type = ?,
                difficulty = ?,
                number_questions = ?,
                current_question = ?,
                question = ?,
                answer = ?,
                answer_submitted = ?,
                feedback = ?,
                scores = ?,
                resume_text = ?,
                updated_at = ?
            WHERE user_id = ?
        """, (
            job_role,
            field,
            experience,
            interview_type,
            difficulty,
            number_questions,
            current_question,
            question,
            answer,
            int(answer_submitted),
            feedback_json,
            scores_json,
            resume_text,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            user_id
        ))

    else:

        cursor.execute("""
            INSERT INTO interview_sessions (
                user_id,
                job_role,
                field,
                experience,
                interview_type,
                difficulty,
                number_questions,
                current_question,
                question,
                answer,
                answer_submitted,
                feedback,
                scores,
                resume_text,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            job_role,
            field,
            experience,
            interview_type,
            difficulty,
            number_questions,
            current_question,
            question,
            answer,
            int(answer_submitted),
            feedback_json,
            scores_json,
            resume_text,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

    conn.commit()
    conn.close()


# =========================================================
# GET SAVED INTERVIEW SESSION
# =========================================================

def get_saved_session(user_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            job_role,
            field,
            experience,
            interview_type,
            difficulty,
            number_questions,
            current_question,
            question,
            answer,
            answer_submitted,
            feedback,
            scores,
            resume_text
        FROM interview_sessions
        WHERE user_id = ?
        LIMIT 1
    """, (user_id,))

    data = cursor.fetchone()

    conn.close()

    if not data:
        return None

    try:
        feedback = json.loads(data[10]) if data[10] else None
    except Exception:
        feedback = None

    try:
        scores = json.loads(data[11]) if data[11] else []
    except Exception:
        scores = []

    return {
        "job_role": data[0] or "",
        "field": data[1] or "",
        "experience": data[2] or "",
        "interview_type": data[3] or "",
        "difficulty": data[4] or "",
        "number_questions": data[5] or 5,
        "current_question": data[6] or 0,
        "question": data[7] or "",
        "answer": data[8] or "",
        "answer_submitted": bool(data[9]),
        "feedback": feedback,
        "scores": scores,
        "resume_text": data[12] or ""
    }


# =========================================================
# DELETE SAVED SESSION
# =========================================================

def delete_saved_session(user_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM interview_sessions
        WHERE user_id = ?
    """, (user_id,))

    conn.commit()
    conn.close()
def delete_user_interviews(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM interviews
        WHERE user_id = ?
    """, (user_id,))

    conn.commit()
    conn.close()

# =========================================================
# INITIALIZE DATABASE
# =========================================================

create_database()