import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
from app import create_app, db
from app.models import User

# Load environment variables
load_dotenv()

def update_admin_password(username, new_password):
    """Updates the password for an existing admin user."""
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"User '{username}' not found.")
            return

        user.password = generate_password_hash(new_password)
        db.session.commit()
        print(f"Password for user '{username}' has been updated successfully!")

if __name__ == "__main__":
    admin_username = "ilaro-admin"
    new_admin_password = "ilaroyewa"
    
    update_admin_password(admin_username, new_admin_password)