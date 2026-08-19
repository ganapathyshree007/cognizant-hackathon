import sqlite3
import pandas as pd
import json

db_path = 'data/patient_features.db'
conn = sqlite3.connect(db_path)
df = pd.read_sql_query("SELECT * FROM patient_features WHERE PATIENT_ID = '00126cb9-8460-4747-e302-c3609684531e'", conn)
conn.close()

result = {
    "exists": len(df) > 0,
    "row_count": len(df),
    "feature_count": len(df.columns) if len(df) > 0 else 0,
    "columns": list(df.columns) if len(df) > 0 else []
}
print(json.dumps(result, indent=2))
