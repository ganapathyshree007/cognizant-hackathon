import sqlite3
import pandas as pd
import json

db_path = 'data/patient_features.db'
conn = sqlite3.connect(db_path)
df = pd.read_sql_query("SELECT * FROM patient_features WHERE PATIENT_ID = '00126cb9-8460-4747-e302-c3609684531e' AND ENCOUNTER_ID = 'UNKNOWN'", conn)
conn.close()

result = {
    "row_count": len(df)
}
print(json.dumps(result, indent=2))
