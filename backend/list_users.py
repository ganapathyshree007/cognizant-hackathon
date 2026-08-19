import os
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://rjciwhclrmwpobinvbqd.supabase.co")
SUPABASE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY", "sb_publishable_6UHYXssCv-G45CFuXWSGig_c10iZSMq")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
# We can just fetch profiles since it's readable
res = supabase.table("profiles").select("*").execute()
print("PROFILES:")
for p in res.data:
    print(p)
