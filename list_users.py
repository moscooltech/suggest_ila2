import os
from dotenv import load_dotenv
from app import create_app, db
from app.models import User

# Load environment variables
load_dotenv()

def list_users():
    """Lists all users in the database with their details."""
    app = create_app()
    with app.app_context():
        users = User.query.all()

        if not users:
            print("❌ No users found in the database")
            return

        print("📋 Users in the database:")
        print("=" * 120)
        print(f"{'ID':<3} {'Username':<20} {'Email':<30} {'Admin':<6} {'Active':<7} {'Verified':<9} {'Created':<20} {'Password Hash':<30}")
        print("=" * 120)

        for user in users:
            admin_status = "✅" if user.is_admin else "❌"
            active_status = "✅" if user.is_active else "❌"
            verified_status = "✅" if user.email_verified else "❌"
            created_date = user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else "N/A"
            password_hash = user.password[:30] + "..." if len(user.password) > 30 else user.password

            print(f"{user.id:<3} {user.username:<20} {user.email:<30} {admin_status:<6} {active_status:<7} {verified_status:<9} {created_date:<20} {password_hash:<30}")

        print("=" * 80)
        print(f"Total users: {len(users)}")

        # Check for admin users specifically
        admin_users = [user for user in users if user.is_admin]
        if admin_users:
            print(f"\n👑 Admin users ({len(admin_users)}):")
            for admin in admin_users:
                print(f"   - {admin.username} ({admin.email})")
        else:
            print("\n⚠️  No admin users found!")

if __name__ == "__main__":
    list_users()