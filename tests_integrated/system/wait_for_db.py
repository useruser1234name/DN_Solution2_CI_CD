# scripts/wait_for_db.py
import os, time, sys
import psycopg2

url = os.getenv("DATABASE_URL")
if not url:
    print("DATABASE_URL not set"); sys.exit(1)

attempts = int(os.getenv("DB_WAIT_ATTEMPTS", "60"))
delay = float(os.getenv("DB_WAIT_DELAY", "1.0"))

for i in range(1, attempts + 1):
    try:
        conn = psycopg2.connect(url, connect_timeout=3)
        conn.close()
        print("DB ready")
        sys.exit(0)
    except Exception as e:
        print(f"DB not ready (try {i}/{attempts}): {e}")
        time.sleep(delay)

print("DB not ready: giving up")
sys.exit(1)
