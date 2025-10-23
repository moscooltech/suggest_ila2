#!/usr/bin/env python3
"""
Script to add image_data and image_mimetype columns to existing MySQL tables.
Run this after the basic tables are created to add the new image storage columns.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()

def add_image_columns():
    """Add image columns to MySQL database"""

    # Get database URL
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        return False

    print("🔧 Adding image columns to MySQL database...")

    try:
        # Create engine
        engine = create_engine(database_url, echo=False)

        with engine.connect() as connection:
            # Add image_data column (LONGBLOB for binary data)
            try:
                connection.execute(text("ALTER TABLE suggestion ADD COLUMN image_data LONGBLOB"))
                connection.commit()
                print("✅ Added image_data column to suggestion table")
            except Exception as e:
                if "column 'image_data' already exists" in str(e).lower():
                    print("⚠️ image_data column already exists")
                else:
                    print(f"❌ Failed to add image_data column: {e}")
                    return False

            # Add image_mimetype column
            try:
                connection.execute(text("ALTER TABLE suggestion ADD COLUMN image_mimetype VARCHAR(50)"))
                connection.commit()
                print("✅ Added image_mimetype column to suggestion table")
            except Exception as e:
                if "column 'image_mimetype' already exists" in str(e).lower():
                    print("⚠️ image_mimetype column already exists")
                else:
                    print(f"❌ Failed to add image_mimetype column: {e}")
                    return False

        print("🎉 Image columns added successfully!")
        return True

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

if __name__ == '__main__':
    success = add_image_columns()
    if success:
        print("\n📋 Next steps:")
        print("1. Run validation: python validate_mysql_migration.py")
        print("2. Test your application at http://localhost:5000")
    else:
        print("\n❌ Failed to add image columns. Check your database connection.")