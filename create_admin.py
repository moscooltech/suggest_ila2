import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
from app import create_app, db
from app.models import User

# Load environment variables
load_dotenv()

def add_admin_user(username, password, email=None):
    """Adds a new admin user to the database."""
    app = create_app()
    with app.app_context():
        if User.query.filter_by(username=username).first():
            print(f"User '{username}' already exists.")
            return

        if email and User.query.filter_by(email=email).first():
            print(f"Email '{email}' is already registered.")
            return

        new_admin = User(
            username=username,
            password=generate_password_hash(password),
            email=email if email else f"{username}@example.com",
            is_admin=True,
            email_verified=True  # Automatically verify admin email
        )
        db.session.add(new_admin)
        db.session.commit()
        print(f"Admin user '{username}' created successfully!")

if __name__ == "__main__":
    admin_username = "ilaro-admin"
    admin_password = "ilaro-yewa"
    
    add_admin_user(admin_username, admin_password)