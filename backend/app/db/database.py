"""
AegisPay-Controller: Database Persistence Engine
Supports SQLite by default (zero setup local file) and PostgreSQL / Supabase via DATABASE_URL.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Default to local SQLite database in app directory, or use cloud/container DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./aegispay.db")

# SQLite needs connect_args check_same_thread=False for multi-threaded FastAPI access
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI Dependency for database session injection"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initializes tables and seeds default merchant profiles if not present"""
    from app.db import models
    Base.metadata.create_all(bind=engine)
    
    # Auto-seed default merchants
    db = SessionLocal()
    try:
        from app.db.repository import seed_default_merchants
        seed_default_merchants(db)
    finally:
        db.close()
