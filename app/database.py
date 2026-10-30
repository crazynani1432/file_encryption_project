import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Base directories & explicit .env loading
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
_env_path = os.path.join(PROJECT_ROOT, ".env")
if os.path.exists(_env_path):
    load_dotenv(_env_path)
else:
    load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./secure_vault.db").strip()

# SQLAlchemy 1.4+ / 2.0+ requires 'postgresql://' instead of legacy 'postgres://' (used by Supabase / Heroku)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Configure connection parameters based on database dialect
engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # Cloud PostgreSQL (Supabase / Neon / Render Postgres) resilience settings
    # pool_pre_ping tests connection health and transparently reconnects if disconnected
    # pool_recycle recycles connections every 5 minutes to stay in sync with cloud poolers
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 300

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    FastAPI dependency that provides a transactional database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
