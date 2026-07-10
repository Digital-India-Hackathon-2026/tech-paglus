import sqlite3
import os
import json
from typing import Any

DB_PATH = "database.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Consent table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS consent (
            farmer_name TEXT PRIMARY KEY,
            consent INTEGER
        )
    """)
    
    # Profile table (storing details only if consent given)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            farmer_name TEXT PRIMARY KEY,
            location TEXT,
            crop TEXT,
            soil_type TEXT,
            season TEXT,
            land_type TEXT,
            irrigation_available INTEGER,
            farm_area_acres REAL,
            budget_per_acre REAL,
            preferred_language TEXT,
            nutrients TEXT
        )
    """)
    
    # Check if nutrients column exists in case db already existed
    try:
        cursor.execute("ALTER TABLE profiles ADD COLUMN nutrients TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
        
    # Feedback table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_name TEXT,
            crop TEXT,
            location TEXT,
            soil_type TEXT,
            useful INTEGER,
            rating INTEGER,
            comments TEXT,
            saved_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def set_consent(farmer_name: str, consent: bool):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO consent (farmer_name, consent) VALUES (?, ?)",
        (farmer_name, 1 if consent else 0)
    )
    conn.commit()
    conn.close()
    
    if not consent:
        # Delete profile memory if consent is revoked
        delete_profile(farmer_name)

def get_consent(farmer_name: str) -> bool:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT consent FROM consent WHERE farmer_name = ?", (farmer_name,))
    row = cursor.fetchone()
    conn.close()
    return bool(row[0]) if row else False

def save_profile(farmer_name: str, profile: dict[str, Any]):
    if not get_consent(farmer_name):
        return  # Do not store without consent
        
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    nutrients_val = profile.get("nutrients")
    nutrients_str = json.dumps(nutrients_val) if nutrients_val else None
    
    cursor.execute(
        """
        INSERT OR REPLACE INTO profiles 
        (farmer_name, location, crop, soil_type, season, land_type, irrigation_available, farm_area_acres, budget_per_acre, preferred_language, nutrients)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            farmer_name,
            profile.get("location"),
            profile.get("crop"),
            profile.get("soil_type"),
            profile.get("season"),
            profile.get("land_type"),
            1 if profile.get("irrigation_available", True) else 0,
            profile.get("farm_area_acres"),
            profile.get("budget_per_acre"),
            profile.get("preferred_language"),
            nutrients_str
        )
    )
    conn.commit()
    conn.close()

def get_profile(farmer_name: str) -> dict[str, Any] | None:
    if not get_consent(farmer_name):
        return None
        
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM profiles WHERE farmer_name = ?", (farmer_name,))
    row = cursor.fetchone()
    conn.close()
    if row:
        profile = dict(row)
        profile["irrigation_available"] = bool(profile["irrigation_available"])
        if profile.get("nutrients"):
            try:
                profile["nutrients"] = json.loads(profile["nutrients"])
            except Exception:
                profile["nutrients"] = {}
        else:
            profile["nutrients"] = {}
        return profile
    return None

def delete_profile(farmer_name: str):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM profiles WHERE farmer_name = ?", (farmer_name,))
    conn.commit()
    conn.close()

def save_feedback(farmer_name: str, crop: str, location: str, soil_type: str, useful: bool, rating: int, comments: str = None):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO feedback (farmer_name, crop, location, soil_type, useful, rating, comments)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (farmer_name, crop, location, soil_type, 1 if useful else 0, rating, comments)
    )
    conn.commit()
    conn.close()

def get_feedback_history(farmer_name: str) -> list[dict[str, Any]]:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT crop, location, soil_type, useful, rating, comments, saved_at FROM feedback WHERE farmer_name = ? ORDER BY id DESC LIMIT 50",
        (farmer_name,)
    )
    rows = cursor.fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["useful"] = bool(d["useful"])
        result.append(d)
    return result
