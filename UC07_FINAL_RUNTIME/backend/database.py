import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
# We use the service key in the backend as per user request to bypass RLS when necessary (e.g. creating encounters programmatically if needed)
# However, for endpoints where we act on behalf of the user, we will pass the user's JWT.
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("WARNING: SUPABASE_URL or SUPABASE_SERVICE_KEY not set. Operating in mock/degraded mode if not handled.")
        # We can still return a client if they are set
        return None
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
