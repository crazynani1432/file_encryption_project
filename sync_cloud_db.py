"""
SecureVault - Cloud Database Synchronizer for Antigravity
Pulls the live database or registered users from your deployed Render instance
and updates your local 'secure_vault.db' so you can view it inside Antigravity / SQLite Viewer.

Usage:
    python sync_cloud_db.py
"""
import os
import sys
import json
import sqlite3
import urllib.request
import urllib.error
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent
_env_path = ROOT_DIR / ".env"
if _env_path.exists():
    load_dotenv(str(_env_path))
else:
    load_dotenv()

DEFAULT_RENDER_URL = "https://file-encryption-project-hp52.onrender.com"
REMOTE_URL = os.getenv("DEPLOYED_URL", DEFAULT_RENDER_URL).rstrip("/")
ADMIN_KEYS = [
    os.getenv("SERVER_MASTER_KEY", "").strip(),
    "fallback_master_key",
    "3a9f02b11e2f89c6708b5e40e6c518b29cd9d8544c7b8e1f0e4b85c1328905fe"
]
ADMIN_KEYS = [k for k in ADMIN_KEYS if k]
LOCAL_DB_PATH = ROOT_DIR / "secure_vault.db"

def sync_users_into_sqlite(users_data):
    """Inserts or updates cloud user records into the local SQLite database."""
    conn = sqlite3.connect(LOCAL_DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            last_login_at TIMESTAMP
        )
    """)

    synced_count = 0
    for u in users_data:
        uid = u.get("id")
        uname = u.get("username")
        email = u.get("email")
        created = u.get("created_at")
        last_login = u.get("last_login_at")

        # Check existing user
        cur.execute("SELECT id FROM users WHERE id = ? OR username = ? OR email = ?", (uid, uname, email))
        row = cur.fetchone()
        if row:
            cur.execute("""
                UPDATE users SET username = ?, email = ?, created_at = ?, last_login_at = ?
                WHERE id = ?
            """, (uname, email, created, last_login, row[0]))
        else:
            cur.execute("""
                INSERT INTO users (id, username, email, password_hash, created_at, last_login_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (uid, uname, email, "[Cloud Bcrypt Hash Protected]", created, last_login))
        synced_count += 1

    conn.commit()
    conn.close()
    return synced_count

def sync_cloud():
    print("=" * 70)
    print(" [SECUREVAULT] Cloud-to-Antigravity Database Synchronizer")
    print("=" * 70)
    print(f"[*] Target Cloud Deployment : {REMOTE_URL}")
    print(f"[*] Local Destination       : {LOCAL_DB_PATH.name}")

    # 1. Attempt full binary SQLite database export with available keys
    print("\n[*] [Method 1] Requesting live database snapshot from cloud...")
    full_export_success = False
    for key in ADMIN_KEYS:
        export_url = f"{REMOTE_URL}/api/admin/export-db?admin_key={key}"
        try:
            req = urllib.request.Request(
                export_url,
                headers={"User-Agent": "SecureVault-Antigravity-Sync/1.0"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                content = resp.read()
                if len(content) > 0:
                    with open(LOCAL_DB_PATH, "wb") as f:
                        f.write(content)
                    print(f"[OK] Downloaded full database ({len(content)} bytes) into {LOCAL_DB_PATH.name}!")
                    full_export_success = True
                    break
        except Exception:
            continue

    if full_export_success:
        print("[OK] Local SQLite database updated successfully!\n")
        from show_users import display_users
        display_users()
        return

    # 2. Fallback: Query /api/users endpoint and sync into local SQLite
    users_url = f"{REMOTE_URL}/api/users"
    print(f"[*] [Method 2] Fetching registered users via public API: {users_url}...")
    try:
        req = urllib.request.Request(
            users_url,
            headers={"User-Agent": "SecureVault-Antigravity-Sync/1.0"}
        )
        with urllib.request.urlopen(req, timeout=25) as resp:
            users_data = json.loads(resp.read().decode("utf-8"))
            count = sync_users_into_sqlite(users_data)
            print(f"[OK] Synced {count} cloud user records into local '{LOCAL_DB_PATH.name}'!\n")

            from show_users import display_users
            display_users()
            return
    except Exception as e:
        print(f"[!] Could not reach {users_url}: {e}")
        print("\nNote: If your Render free instance was idle, it may be waking up from sleep.")
        print("Wait 30-45 seconds and try running this command again:")
        print("    python sync_cloud_db.py\n")

if __name__ == "__main__":
    sync_cloud()
