"""
SwasthAI - SQLite Database Persistence Manager
Stores offline screening records, patient demographics, and doctor prescriptions.
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding='utf-8')

import sqlite3
import os
import time

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "offline_records.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize SQLite tables if they do not exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Patients Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        age INTEGER,
        gender TEXT,
        location TEXT,
        phone TEXT DEFAULT '',
        status TEXT DEFAULT 'Pending Review', -- Pending Review, Prescribed, Escalated
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Ensure phone column exists for existing databases (migration)
    try:
        cursor.execute("ALTER TABLE patients ADD COLUMN phone TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    
    # Screenings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS screenings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        conjunctiva_prob REAL,
        fingernail_prob REAL,
        symptoms TEXT, -- Comma-separated symptom list
        stethoscope_result TEXT, -- Normal, Wheezing, Crackles, None
        heart_rate INTEGER,
        spo2 INTEGER,
        temperature REAL,
        risk_score REAL,
        severity TEXT, -- LOW, MODERATE, HIGH, CRITICAL
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patients(id)
    )
    """)
    
    # Prescriptions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS prescriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        doctor_notes TEXT,
        prescribed_meds TEXT, -- Comma-separated medicines list
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patients(id)
    )
    """)
    
    conn.commit()
    conn.close()
    print("💾 SQLite Database initialized successfully.")

def save_screening(name, age, gender, location, conjunctiva_prob, fingernail_prob, 
                   symptoms, stethoscope_result, heart_rate, spo2, temperature, risk_score, severity, phone=""):
    """
    Save or update patient demographics, write screening results.
    Returns patient_id, screening_id.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if patient already exists (basic match by name and age for simplicity)
    cursor.execute("SELECT id FROM patients WHERE name = ? AND age = ?", (name, age))
    row = cursor.fetchone()
    
    if row:
        patient_id = row['id']
        # Reset status to Pending Review on new screening, update location & phone
        cursor.execute("UPDATE patients SET status = 'Pending Review', location = ?, phone = ? WHERE id = ?", (location, phone, patient_id))
    else:
        cursor.execute(
            "INSERT INTO patients (name, age, gender, location, phone, status) VALUES (?, ?, ?, ?, ?, ?)",
            (name, age, gender, location, phone, "Pending Review")
        )
        patient_id = cursor.lastrowid
        
    # Format symptoms list as comma-separated string
    symptoms_str = ",".join(symptoms) if isinstance(symptoms, list) else str(symptoms)
    
    cursor.execute(
        """
        INSERT INTO screenings (patient_id, conjunctiva_prob, fingernail_prob, symptoms, 
                                 stethoscope_result, heart_rate, spo2, temperature, risk_score, severity)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (patient_id, conjunctiva_prob, fingernail_prob, symptoms_str, stethoscope_result, 
         heart_rate, spo2, temperature, risk_score, severity)
    )
    screening_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    return patient_id, screening_id

def get_all_cases():
    """Retrieve all patients and their latest screening details for the Doctor Dashboard."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT 
            p.id as patient_id, p.name, p.age, p.gender, p.location, p.phone, p.status, p.created_at as patient_created,
            s.id as screening_id, s.conjunctiva_prob, s.fingernail_prob, s.symptoms, 
            s.stethoscope_result, s.heart_rate, s.spo2, s.temperature, s.risk_score, s.severity,
            s.created_at as screening_created,
            pr.doctor_notes, pr.prescribed_meds, pr.created_at as prescription_created
        FROM patients p
        LEFT JOIN screenings s ON s.patient_id = p.id
        LEFT JOIN prescriptions pr ON pr.id = (SELECT MAX(id) FROM prescriptions WHERE patient_id = p.id)
        -- Ensure we get the latest screening and latest prescription per patient
        WHERE s.id = (SELECT MAX(id) FROM screenings WHERE patient_id = p.id)
        ORDER BY s.risk_score DESC, s.id DESC
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    cases = []
    for r in rows:
        cases.append({
            "patient_id": r["patient_id"],
            "name": r["name"],
            "age": r["age"],
            "gender": r["gender"],
            "location": r["location"],
            "phone": r["phone"] if "phone" in r.keys() else "",
            "status": r["status"],
            "screening": {
                "id": r["screening_id"],
                "conjunctiva_prob": r["conjunctiva_prob"],
                "fingernail_prob": r["fingernail_prob"],
                "symptoms": r["symptoms"].split(",") if r["symptoms"] else [],
                "stethoscope_result": r["stethoscope_result"],
                "heart_rate": r["heart_rate"],
                "spo2": r["spo2"],
                "temperature": r["temperature"],
                "risk_score": r["risk_score"],
                "severity": r["severity"],
                "timestamp": r["screening_created"]
            },
            "prescription": {
                "doctor_notes": r["doctor_notes"],
                "prescribed_meds": r["prescribed_meds"].split(",") if r["prescribed_meds"] else [],
                "timestamp": r["prescription_created"]
            } if r["doctor_notes"] else None
        })
        
    conn.close()
    return cases

def add_prescription(patient_id, doctor_notes, prescribed_meds, status="Prescribed"):
    """Save doctor prescription and update patient screening status."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    meds_str = ",".join(prescribed_meds) if isinstance(prescribed_meds, list) else str(prescribed_meds)
    
    # Save prescription
    cursor.execute(
        "INSERT INTO prescriptions (patient_id, doctor_notes, prescribed_meds) VALUES (?, ?, ?)",
        (patient_id, doctor_notes, meds_str)
    )
    
    # Update patient status
    cursor.execute(
        "UPDATE patients SET status = ? WHERE id = ?",
        (status, patient_id)
    )
    
    conn.commit()
    conn.close()
    return True

def get_patient_history(patient_id):
    """Retrieve historical screenings for a specific patient ordered by timestamp."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT risk_score, spo2, heart_rate, temperature, created_at
        FROM screenings
        WHERE patient_id = ?
        ORDER BY created_at ASC
    """
    cursor.execute(query, (patient_id,))
    rows = cursor.fetchall()
    
    history = []
    for r in rows:
        history.append({
            "risk_score": r["risk_score"],
            "spo2": r["spo2"],
            "heart_rate": r["heart_rate"],
            "temperature": r["temperature"],
            "timestamp": r["created_at"]
        })
    conn.close()
    return history

if __name__ == "__main__":
    init_db()
