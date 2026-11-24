
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

print("1. Loading database configuration...")

url = (
    f"postgresql+psycopg://"
    f"{os.getenv('DB_USER')}:"
    f"{os.getenv('DB_PASSWORD')}@"
    f"{os.getenv('DB_HOST')}:"
    f"{os.getenv('DB_PORT')}/"
    f"{os.getenv('DB_NAME')}"
)

print("2. Creating SQLAlchemy engine...")

engine = create_engine(url, pool_pre_ping=True)

print("3. Connecting to PostgreSQL...")

with engine.connect() as connection:
    result = connection.execute(
        text("SELECT current_database(), current_user")
    )

    database, user = result.fetchone()

    print("4. CONNECTION SUCCESSFUL!")
    print("Database:", database)
    print("User:", user)

engine.dispose()

print("5. Test completed!")ss