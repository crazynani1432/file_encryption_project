"""
SecureVault - Registered Users Directory Viewer
Run this tool during presentations or supervisor reviews to display database records.
Works with both local SQLite and Cloud PostgreSQL (Supabase / Render / Neon).
Usage:
    python show_users.py               # View active database users (Local or Cloud)
    python show_users.py --bak         # View users in local secure_vault.db.bak
    python show_users.py --restore-bak # Restore users from backup into secure_vault.db
"""
import os
import sys
import sqlite3
import shutil
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent
_env_path = ROOT_DIR / ".env"
if _env_path.exists():
    load_dotenv(str(_env_path))
else:
    load_dotenv()

DB_PATH = ROOT_DIR / "secure_vault.db"
BAK_PATH = ROOT_DIR / "secure_vault.db.bak"
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./secure_vault.db").strip()

def restore_backup():
    if not BAK_PATH.exists():
        print(f"[!] No backup file found at: {BAK_PATH}")
        return False
    shutil.copy2(BAK_PATH, DB_PATH)
    print(f"[SUCCESS] Restored {BAK_PATH.name} -> {DB_PATH.name} successfully!")
    return True

def fetch_users_from_sqlalchemy():
    from app.database import engine
    from sqlalchemy import text, inspect
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return [], "users table not found"

    cols = [c["name"] for c in inspector.get_columns("users")]
    query = "SELECT id, username, email, created_at, password_hash"
    if "last_login_at" in cols:
        query += ", last_login_at"
    query += " FROM users ORDER BY id ASC"

    with engine.connect() as conn:
        result = conn.execute(text(query))
        rows = [tuple(row) for row in result.fetchall()]
    return rows, None

def fetch_users_from_sqlite(path: Path):
    if not path.exists():
        return [], f"File not found: {path.name}"

    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(users)")
    cols = [col[1] for col in cur.fetchall()]

    query = "SELECT id, username, email, created_at, password_hash"
    if "last_login_at" in cols:
        query += ", last_login_at"
    query += " FROM users ORDER BY id ASC"

    cur.execute(query)
    rows = cur.fetchall()
    conn.close()
    return rows, None

def display_users(use_bak: bool = False):
    is_cloud = (not use_bak) and (not DATABASE_URL.startswith("sqlite"))

    source_label = "Cloud Database" if is_cloud else (BAK_PATH.name if use_bak else DB_PATH.name)

    if use_bak:
        rows, err = fetch_users_from_sqlite(BAK_PATH)
    elif is_cloud:
        try:
            rows, err = fetch_users_from_sqlalchemy()
        except Exception as e:
            rows, err = [], str(e)
    else:
        rows, err = fetch_users_from_sqlite(DB_PATH)

    if err:
        print(f"[!] Error reading users from {source_label}: {err}")
        return

    # Adapt dynamically to current terminal width without awkward wrapping
    term_width = shutil.get_terminal_size((82, 24)).columns
    width = min(max(term_width - 2, 75), 84)

    title = "SECUREVAULT - REGISTERED USERS DIRECTORY"
    if use_bak:
        title += " (BACKUP)"
    elif is_cloud:
        title += " (CLOUD)"

    print("\n" + "=" * width)
    print(title.center(width))
    print("=" * width)
    
    header = f"{'ID':<3} | {'USERNAME':<16} | {'EMAIL':<26} | {'CREATED':<10} | {'HASH'}"
    print(header)
    print("-" * width)

    for r in rows:
        uid = str(r[0])
        raw_uname = str(r[1])
        uname = (raw_uname[:13] + "..") if len(raw_uname) > 16 else raw_uname
        raw_email = str(r[2])
        email = (raw_email[:23] + "..") if len(raw_email) > 26 else raw_email
        created = str(r[3])[:10] if r[3] else "N/A"
        raw_hash = str(r[4]) if len(r) > 4 else ""
        short_hash = (raw_hash[:10] + ".. [Bcrypt]") if len(raw_hash) > 10 else raw_hash

        print(f"{uid:<3} | {uname:<16} | {email:<26} | {created:<10} | {short_hash}")

    print("=" * width)
    print(f"[*] Total Registered Users : {len(rows)}")
    print(f"[*] Source Database        : {source_label}")
    print("[*] Security Architecture  : Bcrypt salted hash (Zero Plaintext Storage)")
    print("=" * width)

    # If active database is empty but backup has users, provide a clear diagnostic tip
    if not use_bak and not is_cloud and len(rows) == 0 and BAK_PATH.exists():
        try:
            b_rows, _ = fetch_users_from_sqlite(BAK_PATH)
            if len(b_rows) > 0:
                print(f"\n[!] NOTICE: Found {len(b_rows)} users inside backup database ({BAK_PATH.name}).")
                print(f"    - To view backup users  : python show_users.py --bak")
                print(f"    - To restore into vault : python show_users.py --restore-bak\n")
        except Exception:
            pass
    print()

if __name__ == "__main__":
    if "--restore-bak" in sys.argv:
        if restore_backup():
            display_users(use_bak=False)
    elif "--bak" in sys.argv:
        display_users(use_bak=True)
    else:
        display_users(use_bak=False)
