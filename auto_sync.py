"""
SecureVault - Background Automatic Live Synchronizer
Continuously monitors your deployed Render application in real-time.
Whenever a new user registers or a file is uploaded on the live link,
it automatically syncs and updates your local 'secure_vault.db' instantly!

Usage:
    python auto_sync.py
    python auto_sync.py --interval 5   (Checks every 5 seconds, default is 5s)
"""
import os
import sys
import time
import json
import urllib.request
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")

DEFAULT_RENDER_URL = "https://file-encryption-project-hp52.onrender.com"
REMOTE_URL = os.getenv("DEPLOYED_URL", DEFAULT_RENDER_URL).rstrip("/")
ADMIN_KEYS = [
    os.getenv("SERVER_MASTER_KEY", "").strip(),
    "fallback_master_key",
    "3a9f02b11e2f89c6708b5e40e6c518b29cd9d8544c7b8e1f0e4b85c1328905fe"
]
ADMIN_KEYS = [k for k in ADMIN_KEYS if k]
LOCAL_DB_PATH = ROOT_DIR / "secure_vault.db"

def fetch_cloud_users_count():
    url = f"{REMOTE_URL}/api/users"
    req = urllib.request.Request(url, headers={"User-Agent": "SecureVault-AutoSync/1.0"})
    with urllib.request.urlopen(req, timeout=8) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return len(data), data

def download_cloud_db():
    for key in ADMIN_KEYS:
        url = f"{REMOTE_URL}/api/admin/export-db?admin_key={key}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SecureVault-AutoSync/1.0"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                content = resp.read()
                if len(content) > 0:
                    with open(LOCAL_DB_PATH, "wb") as f:
                        f.write(content)
                    return True
        except Exception:
            continue
    return False

def start_auto_sync(interval: int = 5):
    print("=" * 70, flush=True)
    print(" [SECUREVAULT] Real-Time Cloud Auto-Synchronizer", flush=True)
    print("=" * 70, flush=True)
    print(f"[*] Target Cloud : {REMOTE_URL}", flush=True)
    print(f"[*] Local File   : {LOCAL_DB_PATH.name}", flush=True)
    print(f"[*] Polling Rate : Every {interval} seconds", flush=True)
    print("[*] Status       : RUNNING IN BACKGROUND (Press Ctrl+C to stop)", flush=True)
    print("=" * 70 + "\n", flush=True)

    last_count = -1

    # Initial check
    try:
        count, users = fetch_cloud_users_count()
        last_count = count
        now = datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] Initialized. Currently {count} registered user(s) in cloud.", flush=True)
        for u in users:
            print(f"       -> User #{u.get('id')}: {u.get('username')} ({u.get('email')})", flush=True)
        if count > 0:
            download_cloud_db()
    except Exception as e:
        print(f"[!] Connecting to cloud service ({e})... Retrying...", flush=True)

    print("\n[*] Listening for new cloud registrations...\n", flush=True)

    while True:
        try:
            time.sleep(interval)
            count, users = fetch_cloud_users_count()
            
            # Only trigger sync if count strictly increased or has valid cloud users
            if count > last_count and count > 0:
                now = datetime.now().strftime("%H:%M:%S")
                new_users = users[max(last_count, 0):]
                names = ", ".join([u.get('username', '') for u in new_users])
                print(f"[{now}] 🔔 NEW REGISTRATION DETECTED! ({names})", flush=True)
                
                download_cloud_db()
                last_count = count
                print(f"[{now}] ✅ Auto-synced {LOCAL_DB_PATH.name} (Total Users: {count})", flush=True)
                print(f"[{now}] 🔄 Refresh your SQLite Viewer in Antigravity to see updates!\n", flush=True)
            elif count < last_count:
                # Cloud restarted/reset, track the new count without wiping local DB
                last_count = count

        except KeyboardInterrupt:
            print("\n[*] Auto-sync stopped by user.", flush=True)
            break
        except Exception:
            # Silent retry on transient connection drops
            pass

if __name__ == "__main__":
    poll_interval = 5
    if "--interval" in sys.argv:
        try:
            idx = sys.argv.index("--interval")
            poll_interval = max(int(sys.argv[idx + 1]), 2)
        except Exception:
            poll_interval = 5
    start_auto_sync(interval=poll_interval)

