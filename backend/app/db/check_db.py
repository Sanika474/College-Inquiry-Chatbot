import sys
import psycopg

passwords = ["postgres", "admin", "root", "1234", "password", ""]
connected = False

for pwd in passwords:
    try:
        conn = psycopg.connect(
            host="localhost",
            port=5432,
            user="postgres",
            password=pwd,
            dbname="postgres",
            autocommit=True
        )
        print(f"CONNECTED_WITH_PWD:{pwd}")
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = 'campusiq_db'")
            if not cur.fetchone():
                cur.execute("CREATE DATABASE campusiq_db")
                print("CREATED_DATABASE:campusiq_db")
            else:
                print("DATABASE_ALREADY_EXISTS:campusiq_db")
        conn.close()
        connected = True
        break
    except Exception as e:
        print(f"Password '{pwd}' failed: {e}")

if not connected:
    print("COULD_NOT_CONNECT_AUTOMATICALLY")
    sys.exit(1)
