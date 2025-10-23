import os
from dotenv import load_dotenv
from app import create_app, db
from app.models import User

# Load environment variables
load_dotenv()

def ensure_admin(username):
    """Ensures that a user has admin privileges."""
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"User '{username}' not found.")
            return

        if user.is_admin:
            print(f"User '{username}' is already an admin.")
        else:
            user.is_admin = True
            db.session.commit()
            print(f"User '{username}' has been granted admin privileges.")

if __name__ == "__main__":
    admin_username = "ilaro-admin"
    ensure_admin(admin_username)