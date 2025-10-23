#!/usr/bin/env python3
"""
WSGI entry point for production deployment with gunicorn.
This file creates the Flask application instance for production use.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import and create the Flask application
from app import create_app

# Create application instance
app = create_app()

# Production configuration override
if __name__ != '__main__':
    app.config['DEBUG'] = False
    app.config['TESTING'] = False

if __name__ == '__main__':
    # Allow running this file directly for testing
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))