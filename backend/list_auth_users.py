import os
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://rjciwhclrmwpobinvbqd.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
try:
    res = supabase.auth.admin.list_users()
    print("USERS:")
    for u in res:
        print(u.email)
except Exception as e:
    print("Error listing users:", e)
