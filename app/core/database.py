# # Database connection test
# def test_connection():
#     try:
#         with engine.connect() as connection:
#             result = connection.execute("SELECT 1")
#             print("Database connection successful!")
#             return True
#     except Exception as e:
#         print(f"Database connection failed: {e}")
#         return False


import os
from typing import Generator
from app.core.config import setting
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

# 1. db url for connection
DATABASE_URL = setting.DATABASE_URL

# 2. Engine
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# 3. Sessions
SessionLocal = sessionmaker(autoflush=False, autocommit=False, bind=engine)

# 4. Base (For models)
Base = declarative_base()


# 5. Creating db instance per request
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
