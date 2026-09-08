import sys
import os

# Add the parent directory to the path so we can import app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

print(f"DATABASE_URL: {settings.DATABASE_URL}")

try:
    from psycopg_pool import ConnectionPool
    from langgraph.checkpoint.postgres import PostgresSaver
    
    conninfo = settings.DATABASE_URL
    if "sslmode" not in conninfo:
        conninfo += "?sslmode=require" if "?" not in conninfo else "&sslmode=require"

    pool = ConnectionPool(conninfo=conninfo)
    checkpointer = PostgresSaver(pool)
    checkpointer.setup()
    print("PostgresSaver setup SUCCESS!")
except Exception as e:
    import traceback
    traceback.print_exc()
