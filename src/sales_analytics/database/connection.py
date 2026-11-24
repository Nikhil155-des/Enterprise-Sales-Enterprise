
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

from sales_analytics.config.settings import (
    DB_HOST,
    DB_PORT,
    DB_NAME,
    DB_USER,
    DB_PASSWORD,
)

# Build PostgreSQL connection URL
database_url = URL.create(
    drivername="postgresql+pg8000",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
)

# Create SQLAlchemy engine
engine = create_engine(
    database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=False,
)

def test_database_connection():

    try:
        with engine.connect() as connection:

            result = connection.exec_driver_sql("""
                SELECT
                    current_database() AS database_name,
                    current_user AS database_user,
                    version() AS database_version
            """)

            database_info = result.fetchone()

            print("PostgreSQL connection successful!")
            print("Database:", database_info.database_name)
            print("User:", database_info.database_user)
            print("Version:", database_info.database_version)

            return True

    except Exception as error:
        print("Database connection failed:", error)
        return False

if __name__ == "__main__":
    test_database_connection()