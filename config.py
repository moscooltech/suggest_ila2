import os

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'static/uploads'

    # Database configuration - defaults to SQLite for development
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///suggestions.db')

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    # Can use SQLite or MySQL for development
    # SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://dev_user:dev_pass@localhost/suggestions_dev'

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False

    # Production should use MySQL
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        SQLALCHEMY_DATABASE_URI = database_url
    else:
        # Fallback to SQLite for development/production flexibility
        SQLALCHEMY_DATABASE_URI = 'sqlite:///suggestions.db'

    # Additional production settings
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config(config_name=None):
    """Get configuration class based on environment"""
    if config_name is None:
        # Check FLASK_ENV first, then fall back to other common environment variables
        config_name = os.environ.get('FLASK_ENV') or os.environ.get('APP_ENV') or 'development'

    return config.get(config_name, config['default'])