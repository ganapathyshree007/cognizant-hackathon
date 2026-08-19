import os
import uuid
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://rjciwhclrmwpobinvbqd.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
email = f"test_{uuid.uuid4().hex[:6]}@test.com"
password = "password123"

print(f"Signing up: {email}")
try:
    res = supabase.auth.admin.create_user({
        "email": email,
        "password": password,
        "email_confirm": True,
        "user_metadata": {"full_name": "Test User", "role": "CARE_MANAGER"}
    })
    print("Sign up response:", res)
except Exception as e:
    print("Sign up failed:", e)
