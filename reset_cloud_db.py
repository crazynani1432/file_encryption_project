"""
SecureVault - Cloud Database Reset Tool
Wipes all registered user accounts and records from the deployed Render cloud database.

Usage:
    python reset_cloud_db.py
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
ADMIN_KEYS = [
    os.getenv("SERVER_MASTER_KEY", "").strip(),
    "fallback_master_key",
    "3a9f02b11e2f89c6708b5e40e6c518b29cd9d8544c7b8e1f0e4b85c1328905fe"
]
ADMIN_KEYS = [k for k in ADMIN_KEYS if k]

def reset_cloud():
    print("=" * 70)
    print(" [SECUREVAULT] Cloud Database Reset Tool")
    print("=" * 70)
    print(f"[*] Target Cloud Deployment : {REMOTE_URL}")
    print("[*] Action                   : WIPE ALL USERS & RECORDS FROM CLOUD")
    print("=" * 70 + "\n")

    success = False
    for key in ADMIN_KEYS:
        url = f"{REMOTE_URL}/api/admin/reset-db?admin_key={key}"
        try:
            req = urllib.request.Request(
                url,
                data=b"",
                headers={"User-Agent": "SecureVault-Reset/1.0"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                print(f"[SUCCESS] Cloud response: {data.get('message')}")
                print(f"[*] Cloud users remaining : {data.get('total_users', 0)}\n")
                success = True
                break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"[i] Reset endpoint deploying to Render. Please wait 30 seconds.")
                break
            elif e.code == 403:
                continue
            else:
                print(f"[!] Server returned HTTP {e.code}: {e.reason}")
        except Exception as e:
            print(f"[!] Connection error: {e}")
            break

    if not success:
        print("[!] Could not reset database yet. Render is either deploying or key mismatch.")
        print("    If Render is redeploying, wait 30-45 seconds and re-run:")
        print("    python reset_cloud_db.py\n")

if __name__ == "__main__":
    reset_cloud()

