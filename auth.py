import sqlite3
import hashlib
import secrets

DB_NAME = "interview.db"


# =========================================================
# PASSWORD HASHING
# =========================================================

def hash_password(password):
    salt = secrets.token_hex(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000
    ).hex()

    return f"{salt}${password_hash}"


def verify_password(password, stored_password):
    try:
        salt, stored_hash = stored_password.split("$")

        password_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100000
        ).hex()

        return secrets.compare_digest(
            password_hash,
            stored_hash
        )

    except Exception:
        return False


# =========================================================
# REGISTER USER
# =========================================================

def register_user(email, password):

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM users WHERE email = ?",
        (email,)
    )

    existing_user = cursor.fetchone()

    if existing_user:
        conn.close()
        return False, "An account with this email already exists."

    password_hash = hash_password(password)

    cursor.execute("""
        INSERT INTO users (
            email,
            password_hash,
            created_at
        )
        VALUES (?, ?, datetime('now'))
    """, (
        email,
        password_hash
    ))

    conn.commit()

    user_id = cursor.lastrowid

    conn.close()

    return True, user_id


# =========================================================
# LOGIN
# =========================================================

def login_user(email, password):

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            email,
            password_hash
        FROM users
        WHERE email = ?
    """, (email,))

    user = cursor.fetchone()

    conn.close()

    if not user:
        return None

    user_id, user_email, stored_password = user

    if verify_password(password, stored_password):

        return {
            "id": user_id,
            "email": user_email
        }

    return None


# =========================================================
# GET USER
# =========================================================

def get_user(user_id):

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, email, created_at
        FROM users
        WHERE id = ?
    """, (user_id,))

    user = cursor.fetchone()

    conn.close()

    return user