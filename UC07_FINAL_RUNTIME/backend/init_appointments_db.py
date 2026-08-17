import sqlite3
import os

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data/appointments.db'))

def init_db():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    c.execute('''
    CREATE TABLE IF NOT EXISTS appointments (
        appointment_id TEXT PRIMARY KEY,
        patient_id TEXT,
        encounter_id TEXT,
        provider_name TEXT,
        provider_npi TEXT,
        pac_id TEXT,
        provider_specialty TEXT,
        appointment_date TEXT,
        appointment_time TEXT,
        status TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    c.execute('''
    CREATE TABLE IF NOT EXISTS outcomes (
        outcome_id TEXT PRIMARY KEY,
        appointment_id TEXT,
        patient_id TEXT,
        clinical_notes TEXT,
        follow_up_required BOOLEAN,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(appointment_id) REFERENCES appointments(appointment_id)
    )
    ''')
    
    conn.commit()
    conn.close()
    print("appointments.db initialized successfully!")

if __name__ == "__main__":
    init_db()
