import os
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://rjciwhclrmwpobinvbqd.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

cm_email = "cm@test.com"
patient_email = "patient@test.com"
password = "password123"

print("Creating Care Manager...")
try:
    supabase.auth.admin.create_user({
        "email": cm_email,
        "password": password,
        "email_confirm": True,
        "user_metadata": {"full_name": "Test CM", "role": "CARE_MANAGER"}
    })
    print("Care Manager created.")
except Exception as e:
    print("CM:", e)

print("Creating Patient...")
try:
    supabase.auth.admin.create_user({
        "email": patient_email,
        "password": password,
        "email_confirm": True,
        "user_metadata": {"full_name": "Test Patient", "role": "PATIENT"}
    })
    print("Patient created.")
except Exception as e:
    print("Patient:", e)
