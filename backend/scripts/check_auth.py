import sys
import os
import psycopg2

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.core.config import settings

conn = psycopg2.connect(settings.DATABASE_URL)
cur = conn.cursor()

cur.execute("SELECT id, email FROM auth.users;")
users = cur.fetchall()

installation_id_base = 1234567
for i, user in enumerate(users):
    user_id = user[0]
    inst_id = installation_id_base + i
    cur.execute("""
        INSERT INTO installations (user_id, installation_id, repositories)
        VALUES (%s, %s, '["imshreyaskn/realive-test-target"]')
        ON CONFLICT (installation_id) DO UPDATE 
        SET repositories = EXCLUDED.repositories
    """, (user_id, inst_id))
    print(f"Inserted installation manually for user: {user[1]}")

conn.commit()
cur.close()
conn.close()
