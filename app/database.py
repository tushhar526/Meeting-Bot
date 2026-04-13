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
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. db url for connection
DATABASE_URL = os.getenv("DATABASE_URL")

# 2. Engine
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# 3. Sessions
SessionLocal = sessionmaker(autoflush=False, autocommit=False, bind=engine)

# 4. Base (For models)
Base = declarative_base()


# 5. Creating db instance per request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
