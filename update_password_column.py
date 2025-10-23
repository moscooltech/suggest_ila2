import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

def update_password_column():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("DATABASE_URL not set.")
        return

    try:
        engine = create_engine(database_url)
        with engine.connect() as connection:
            connection.execute(text('ALTER TABLE "user" ALTER COLUMN password TYPE VARCHAR(255);'))
            connection.commit()
            print("Successfully updated password column to VARCHAR(255).")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    update_password_column()