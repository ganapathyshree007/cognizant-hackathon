import os
from supabase import create_client

url = "https://rjciwhclrmwpobinvbqd.supabase.co"
key = "sb_publishable_6UHYXssCv-G45CFuXWSGig_c10iZSMq"
client = create_client(url, key)

try:
    resp = client.table('patient_features').select('PATIENT_ID', count='exact').limit(1).execute()
    print("Patient features count:", resp.count)
except Exception as e:
    print("Error querying patient_features:", e)

try:
    resp = client.table('appointments').select('*', count='exact').limit(1).execute()
    print("Appointments count:", resp.count)
except Exception as e:
    print("Error querying appointments:", e)
