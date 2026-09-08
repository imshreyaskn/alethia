import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.client import db

runs = db.table("pipeline_runs").select("*").order("created_at", desc=True).limit(3).execute()
print("Latest Runs:", runs.data)
