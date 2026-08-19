import os
import sqlite3
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client
import sys

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def migrate_table(sqlite_path, table_name, supabase_table):
    if not os.path.exists(sqlite_path):
        print(f"Skipping {sqlite_path}: File not found.")
        return
        
    print(f"Migrating {table_name} from {sqlite_path} to Supabase table {supabase_table}...")
    try:
        conn = sqlite3.connect(sqlite_path)
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        conn.close()
        
        if df.empty:
            print(f"No records found in {table_name}.")
            return
            
        records = df.to_dict(orient="records")
        
        # Batch insert to avoid payload limits
        batch_size = 500
        for i in range(0, len(records), batch_size):
            batch = records[i:i+batch_size]
            response = supabase.table(supabase_table).insert(batch).execute()
            print(f"Inserted batch {i//batch_size + 1} ({len(batch)} records) into {supabase_table}")
            
        print(f"Successfully migrated {len(records)} records for {supabase_table}.")
    except Exception as e:
        print(f"Error migrating {table_name}: {e}")

if __name__ == "__main__":
    print("Starting migration to Supabase...")
    
    # Migrate appointments
    migrate_table(
        sqlite_path=os.path.join(os.path.dirname(__file__), 'appointments.db'),
        table_name='appointments',
        supabase_table='appointments'
    )
    
    # Migrate outcomes
    migrate_table(
        sqlite_path=os.path.join(os.path.dirname(__file__), 'appointments.db'),
        table_name='outcomes',
        supabase_table='outcomes'
    )
    
    # Migrate patient_features
    migrate_table(
        sqlite_path=os.path.join(os.path.dirname(__file__), 'data/patient_features.db'),
        table_name='patient_features',
        supabase_table='patient_features'
    )
    
    print("Migration script completed.")
