from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os
from config import get_config

db = SQLAlchemy()
login_manager = LoginManager()


@login_manager.user_loader
def load_user(user_id):
    from .models import User
    return User.query.get(int(user_id))

def create_app(config_name=None):
    app = Flask(__name__, template_folder='../templates', static_folder='../static')

    # Load configuration
    config_class = get_config(config_name)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'admin.login'

    from .routes import bp as main_bp
    app.register_blueprint(main_bp)

    from .admin_routes import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    with app.app_context():
        db.create_all()

    return app