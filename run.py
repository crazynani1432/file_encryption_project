"""
Application Launcher for Secure Multi-Tier File Vault
"""
import os
import uvicorn
from dotenv import load_dotenv

# Load environment configuration from .env if present
load_dotenv()

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "true").lower() in ("true", "1", "yes")

    print(f"[*] Starting Secure Vault on http://{host}:{port}...")
    uvicorn.run("app.main:app", host=host, port=port, reload=reload)
