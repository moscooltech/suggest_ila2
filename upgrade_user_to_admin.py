import os
from dotenv import load_dotenv
from app import create_app, db
from app.models import User

# Load environment variables
load_dotenv()

def upgrade_user_to_admin(username):
    """Upgrades an existing user to admin privileges."""
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"❌ User '{username}' not found.")
            return

        if user.is_admin:
            print(f"ℹ️  User '{username}' is already an admin.")
            return

        user.is_admin = True
        db.session.commit()
        print(f"✅ User '{username}' has been upgraded to admin successfully!")

if __name__ == "__main__":
    # Upgrade the mikedongle user to admin
    upgrade_user_to_admin("mikedongle")