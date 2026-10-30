"""
Database Connection & Schema Verification Tool
Use this script to verify your connection to Supabase PostgreSQL or local SQLite.
Usage:
    python verify_db.py
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure root path is loaded
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

# Explicitly load .env
_env_path = ROOT_DIR / ".env"
if _env_path.exists():
    load_dotenv(str(_env_path))
else:
    load_dotenv()

from app.database import engine, Base
from app import models
from sqlalchemy import inspect, text

def check_database():
    print("=" * 60)
    print(" [SECUREVAULT] Database Connection Diagnostic")
    print("=" * 60)
    
    db_url = os.getenv("DATABASE_URL", "sqlite:///./secure_vault.db")
    # Hide password for safe terminal output
    safe_url = db_url
    if "@" in safe_url and "://" in safe_url:
        prefix, rest = safe_url.split("://", 1)
        creds, host = rest.split("@", 1)
        if ":" in creds:
            user = creds.split(":", 1)[0]
            safe_url = f"{prefix}://{user}:*****@{host}"

    print(f"[*] Configured Database URL : {safe_url}")
    print(f"[*] Dialect                : {engine.dialect.name.upper()}")

    try:
        # Test basic connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).fetchone()
            print("[OK] Raw Database Connection: SUCCESS")

        # Initialize tables
        print("[*] Synchronizing table schemas (users, encrypted_files, active_otps)...")
        models.Base.metadata.create_all(bind=engine)
        print("[OK] Tables verified & synchronized successfully!")

        # Inspect tables
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"[OK] Tables present in database: {', '.join(tables)}")

        # Query users count
        with engine.connect() as conn:
            user_count = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
            file_count = conn.execute(text("SELECT COUNT(*) FROM encrypted_files")).scalar()
            print(f"[OK] Active registered users: {user_count}")
            print(f"[OK] Encrypted file records : {file_count}")

        print("\n" + "=" * 60)
        print(" [SUCCESS] Database is 100% HEALTHY and READY!")
        print("=" * 60 + "\n")

    except Exception as e:
        print("\n" + "!" * 60)
        print(f" [!] Connection failed: {e}")
        print("!" * 60 + "\n")
        print("Troubleshooting tips:")
        print("1. If using Supabase, make sure you replaced [YOUR-PASSWORD] with your actual database password.")
        print("2. Use the Session or Transaction Pooler connection string (port 6543 or 5432).")
        print("3. Check that your IP or 0.0.0.0/0 is allowed in Supabase Network Settings (default is open to all).")

def migrate_sqlite_to_cloud():
    """Migrates existing records from local SQLite to the configured cloud database (Supabase)."""
    sqlite_path = ROOT_DIR / "secure_vault.db"
    if not sqlite_path.exists():
        print("[!] No local secure_vault.db found to migrate.")
        return

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    sqlite_engine = create_engine(f"sqlite:///{sqlite_path}", connect_args={"check_same_thread": False})
    SqliteSession = sessionmaker(bind=sqlite_engine)
    CloudSession = sessionmaker(bind=engine)

    print("\n[*] Starting migration from local SQLite -> Cloud Database...")
    with SqliteSession() as src, CloudSession() as dst:
        # 1. Users
        users = src.query(models.User).all()
        migrated_users = 0
        for u in users:
            existing = dst.query(models.User).filter(models.User.username == u.username).first()
            if not existing:
                dst.add(models.User(
                    id=u.id,
                    username=u.username,
                    email=u.email,
                    password_hash=u.password_hash,
                    created_at=u.created_at
                ))
                migrated_users += 1
        dst.commit()
        print(f"[OK] Migrated {migrated_users} new users into cloud database.")

        # 2. Encrypted files
        files = src.query(models.EncryptedFile).all()
        migrated_files = 0
        for f in files:
            existing = dst.query(models.EncryptedFile).filter(models.EncryptedFile.id == f.id).first()
            if not existing:
                dst.add(models.EncryptedFile(
                    id=f.id,
                    filename=f.filename,
                    filepath=f.filepath,
                    access_policy=f.access_policy,
                    sender_id=f.sender_id,
                    recipient_email=f.recipient_email,
                    security_question=f.security_question,
                    encrypted_file_key=f.encrypted_file_key,
                    download_count=f.download_count,
                    created_at=f.created_at
                ))
                migrated_files += 1
        dst.commit()
        print(f"[OK] Migrated {migrated_files} file records into cloud database.")

    print("[SUCCESS] Data migration completed successfully!\n")

if __name__ == "__main__":
    check_database()
    if "--migrate-from-sqlite" in sys.argv:
        migrate_sqlite_to_cloud()
