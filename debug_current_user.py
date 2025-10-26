import os
from dotenv import load_dotenv
from flask import Flask, session, g
from flask_login import current_user, login_required
from app import create_app, db
from app.models import User

# Load environment variables
load_dotenv()

app = create_app()

@app.route('/debug_user')
@login_required
def debug_user():
    """Debug endpoint to check current user status"""
    user_info = {
        'username': current_user.username,
        'email': current_user.email,
        'is_admin': current_user.is_admin,
        'is_active': current_user.is_active,
        'email_verified': current_user.email_verified,
        'id': current_user.id
    }
    return user_info

if __name__ == "__main__":
    print("Debug script - this should be run on the deployed server")
    print("Visit /debug_user endpoint when logged in to see user status")