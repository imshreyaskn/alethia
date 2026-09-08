import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.client import db

users = db.table("users").select("*").execute() # Actually Supabase doesn't let you query auth.users from public schema easily unless using admin client.
print("Users:", users.data)
