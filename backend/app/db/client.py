"""
client.py — Supabase database client (singleton)

WHAT IS A SINGLETON?
We only want ONE Supabase client instance for the entire backend — not a new
one created on every request. This module creates it once and exports it.
Every other file that needs the database imports 'db' from here.

HOW SUPABASE CLIENT WORKS:
The client uses your SUPABASE_URL and SUPABASE_SERVICE_KEY to authenticate
and connect to your Postgres database. You then use it like:

    result = db.table("pipeline_runs").select("*").execute()
    result = db.table("pipeline_runs").insert({...}).execute()
    result = db.table("pipeline_runs").update({...}).eq("id", run_id).execute()
"""
from supabase import create_client, Client
from app.core.config import settings

# Create the single shared Supabase client instance
# This authenticates using the service role key, giving full DB access
db: Client = create_client(
    supabase_url=settings.SUPABASE_URL,
    supabase_key=settings.SUPABASE_SERVICE_KEY,
)
