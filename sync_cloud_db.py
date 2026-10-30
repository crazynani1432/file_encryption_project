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
ADMIN_KEY = os.getenv("SERVER_MASTER_KEY", "").strip()
LOCAL_DB_PATH = ROOT_DIR / "secure_vault.db"

def sync_cloud():
    print("=" * 70)
    print(" [SECUREVAULT] Cloud-to-Antigravity Database Synchronizer")
    print("=" * 70)
    print(f"[*] Target Cloud Deployment : {REMOTE_URL}")
    print(f"[*] Local Destination       : {LOCAL_DB_PATH.name}")

    # 1. Attempt full binary SQLite database export
    export_url = f"{REMOTE_URL}/api/admin/export-db?admin_key={ADMIN_KEY}"
    print("\n[*] [Method 1] Requesting live database snapshot from cloud...")
    try:
        req = urllib.request.Request(
            export_url,
            headers={"User-Agent": "SecureVault-Antigravity-Sync/1.0"}
        )
        with urllib.request.urlopen(req, timeout=25) as resp:
            content = resp.read()
            if len(content) > 0:
                with open(LOCAL_DB_PATH, "wb") as f:
                    f.write(content)
                print(f"[OK] Downloaded live database ({len(content)} bytes) into {LOCAL_DB_PATH.name}!")
                print("[OK] You can now open 'secure_vault.db' in Antigravity SQLite Viewer or run 'python show_users.py'!\n")
                
                # Display via show_users
                from show_users import display_users
                display_users()
                return
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print("[i] Export endpoint not yet deployed to cloud. Falling back to /api/users...")
        elif e.code == 403:
            print(f"[!] Access denied (403). Check that SERVER_MASTER_KEY in your local .env matches Render.")
        else:
            print(f"[!] Cloud export returned status {e.code}: {e.reason}")
    except Exception as e:
        print(f"[!] Cloud connection error: {e}")

    # 2. Fallback: Query /api/users JSON endpoint
    users_url = f"{REMOTE_URL}/api/users"
    print(f"[*] [Method 2] Fetching registered users via public API: {users_url}...")
    try:
        req = urllib.request.Request(
            users_url,
            headers={"User-Agent": "SecureVault-Antigravity-Sync/1.0"}
        )
        with urllib.request.urlopen(req, timeout=25) as resp:
            users_data = json.loads(resp.read().decode("utf-8"))
            print(f"\n[OK] Successfully retrieved {len(users_data)} users from cloud:")
            print("-" * 65)
            print(f"{'ID':<4} | {'USERNAME':<16} | {'EMAIL':<28} | {'CREATED'}")
            print("-" * 65)
            for u in users_data:
                uid = str(u.get("id", ""))
                uname = str(u.get("username", ""))[:16]
                email = str(u.get("email", ""))[:28]
                created = str(u.get("created_at", ""))[:10]
                print(f"{uid:<4} | {uname:<16} | {email:<28} | {created}")
            print("-" * 65 + "\n")
    except Exception as e:
        print(f"[!] Could not reach {users_url}: {e}")
        print("\nNote: If your Render free instance was idle, it may be waking up from sleep.")
        print("Wait 30-45 seconds and try running this command again:")
        print("    python sync_cloud_db.py\n")

if __name__ == "__main__":
    sync_cloud()

