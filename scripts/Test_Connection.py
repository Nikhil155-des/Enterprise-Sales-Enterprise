
from sqlalchemy import text

from sales_analytics.database.connection import engine

def main():

    with engine.connect() as connection:

        result = connection.execute(
            text("""
                SELECT COUNT(*) AS total_tables
                FROM information_schema.tables
                WHERE table_schema = 'analytics'
                  AND table_type = 'BASE TABLE'
            """)
        )

        total_tables = result.scalar_one()

        print("Connected to PostgreSQL successfully!")
        print(f"Database tables found: {total_tables}")

        if total_tables != 13:
            raise RuntimeError(
                f"Expected 13 tables, found {total_tables}"
            )

        print("Database schema verification successful!")

if __name__ == "__main__":
    main()