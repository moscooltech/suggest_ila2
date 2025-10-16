from app import create_app, db
from sqlalchemy import text

app = create_app()

def migrate_database():
    with app.app_context():
        try:
            # Add is_admin column to user table if it doesn't exist
            db.session.execute(text("ALTER TABLE user ADD COLUMN is_admin BOOLEAN DEFAULT 0"))
            db.session.commit()
            print("✅ Added is_admin column to user table")

            # Set admin user as admin
            result = db.session.execute(text("UPDATE user SET is_admin = 1 WHERE username = 'admin'"))
            if result.rowcount > 0:
                print("✅ Set admin user as administrator")
            else:
                print("⚠️ Admin user not found, you may need to create it")

            db.session.commit()
            print("✅ Database migration completed successfully!")

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            print("This might be because the column already exists or another issue.")
            db.session.rollback()

if __name__ == '__main__':
    migrate_database()