import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.client import db

run = db.table("pipeline_runs").select("*").eq("id", "97634fc9-12ac-4190-9ff3-c0d0d3a280cf").execute()
print("Run:", run.data)

installations = db.table("installations").select("*").execute()
print("Installations:", installations.data)
