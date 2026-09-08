import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if "--confirm" not in sys.argv:
    print("WARNING: This will delete all rows from fix_history, pipeline_runs, and installations.")
    print("To proceed, run: python wipe_db.py --confirm")
    sys.exit(1)

from app.db.client import db
import time

print("Wiping fix_history...")
res1 = db.table("fix_history").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
print(f"Deleted {len(res1.data)} records from fix_history")

print("Wiping pipeline_runs...")
res2 = db.table("pipeline_runs").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
print(f"Deleted {len(res2.data)} records from pipeline_runs")

print("Wiping installations...")
res3 = db.table("installations").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
print(f"Deleted {len(res3.data)} records from installations")

print("Database wiped completely!")
