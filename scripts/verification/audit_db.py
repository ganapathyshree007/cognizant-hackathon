import sqlite3
import pandas as pd
from pathlib import Path
import os
ROOT = Path(r'd:\cognizant-hackathon-main')
c = sqlite3.connect(ROOT/'provider_catalog'/'provider_catalog.sqlite')
df = pd.read_sql_query('SELECT * FROM providers', c)
print(f'providers = {len(df)}')
print(f'providers_missing_specialty = {df.primary_specialty.isna().sum()}')
print(f'providers_missing_location = {(df.city.isna() | df.state.isna()).sum()}')
print('Columns:', df.columns.tolist())

cursor = c.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [r[0] for r in cursor.fetchall()]
print('Tables:', tables)

if 'facilities' in tables:
    df_fac = pd.read_sql_query('SELECT * FROM facilities', c)
    print(f'facilities = {len(df_fac)}')
else:
    print('facilities = 0 (No facilities table)')

print(f"telehealth_YES = {len(df[df.telehealth_available == 'YES'])}")
print(f"telehealth_NO = {len(df[df.telehealth_available == 'NO'])}")
print(f"telehealth_missing = {df.telehealth_available.isna().sum()}")
