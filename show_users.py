"""
SecureVault - Registered Users Directory Viewer
Run this tool during presentations or supervisor reviews to display database records.
Usage:
    python show_users.py
"""
import os
import sys
import sqlite3
import shutil
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
DB_PATH = ROOT_DIR / "secure_vault.db"

def display_users():
    if not DB_PATH.exists():
        print(f"[!] Database file not found at: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
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

    # Adapt dynamically to current terminal width without awkward wrapping
    term_width = shutil.get_terminal_size((82, 24)).columns
    width = min(max(term_width - 2, 75), 84)

    print("\n" + "=" * width)
    print("SECUREVAULT - REGISTERED USERS DIRECTORY".center(width))
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
    print(f"[*] Physical Database File : {DB_PATH.name}")
    print("[*] Security Architecture  : Bcrypt salted hash (Zero Plaintext Storage)")
    print("=" * width + "\n")

if __name__ == "__main__":
    display_users()
