import sqlite3
import os
from pathlib import Path

def create_demo_database():
    root = Path(os.environ.get('NAVIGATOR_PROJECT_ROOT', r'd:\cognizant-hackathon-main'))
    db_path = root / 'provider_catalog' / 'provider_catalog.sqlite'
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    if db_path.exists():
        db_path.unlink()
        
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # We create a simple provider schema reflecting what's needed for Step 9
    c.executescript("""
        CREATE TABLE providers (
            NPI TEXT PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            primary_specialty TEXT,
            telehealth_available TEXT,
            city TEXT,
            state TEXT,
            zip TEXT,
            phone TEXT,
            mips_score REAL,
            quality_data_available INTEGER,
            affiliated_facility_count INTEGER,
            affiliated_facility_types TEXT
        );
    """)
    
    # 1. Primary Care Provider (State: CA)
    c.execute("""
        INSERT INTO providers (NPI, first_name, last_name, primary_specialty, telehealth_available, city, state, zip, phone, mips_score, quality_data_available, affiliated_facility_count, affiliated_facility_types)
        VALUES ('1111111111', 'Demo', 'Primary Care', 'FAMILY PRACTICE', 'NO', 'San Francisco', 'CA', '94105', '555-0101', 85.0, 1, 1, 'Clinic')
    """)
    
    # 2. Urgent Care Facility (State: CA)
    c.execute("""
        INSERT INTO providers (NPI, first_name, last_name, primary_specialty, telehealth_available, city, state, zip, phone, mips_score, quality_data_available, affiliated_facility_count, affiliated_facility_types)
        VALUES ('2222222222', 'Demo', 'Urgent Care Center', 'URGENT CARE FACILITY', 'NO', 'San Francisco', 'CA', '94105', '555-0102', 90.0, 1, 1, 'Urgent Care')
    """)
    
    # 3. Telehealth Provider (State: CA)
    c.execute("""
        INSERT INTO providers (NPI, first_name, last_name, primary_specialty, telehealth_available, city, state, zip, phone, mips_score, quality_data_available, affiliated_facility_count, affiliated_facility_types)
        VALUES ('3333333333', 'Demo', 'Telehealth Doc', 'INTERNAL MEDICINE', 'YES', 'San Francisco', 'CA', '94105', '555-0103', 95.0, 1, 0, '')
    """)
    
    # 4. Care Management Resource (State: NY)
    c.execute("""
        INSERT INTO providers (NPI, first_name, last_name, primary_specialty, telehealth_available, city, state, zip, phone, mips_score, quality_data_available, affiliated_facility_count, affiliated_facility_types)
        VALUES ('4444444444', 'Demo', 'Care Manager', 'CLINICAL SOCIAL WORKER', 'YES', 'New York', 'NY', '10001', '555-0104', NULL, 0, 0, '')
    """)
    
    # 5. Urgent Care Facility (State: NY)
    c.execute("""
        INSERT INTO providers (NPI, first_name, last_name, primary_specialty, telehealth_available, city, state, zip, phone, mips_score, quality_data_available, affiliated_facility_count, affiliated_facility_types)
        VALUES ('5555555555', 'Demo', 'NY Urgent Care', 'URGENT CARE FACILITY', 'NO', 'New York', 'NY', '10001', '555-0105', 88.0, 1, 1, 'Urgent Care')
    """)
    
    conn.commit()
    conn.close()
    
    print(f"Generated prototype demo provider catalog at {db_path}")

if __name__ == '__main__':
    create_demo_database()
