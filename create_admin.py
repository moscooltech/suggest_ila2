from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    db.create_all()
    # Create default admin user
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@ilaro.com', password=generate_password_hash('admin123'), is_admin=True)
        db.session.add(admin)
        db.session.commit()
        print("Admin user created: username=admin, password=admin123")
    else:
        print("Admin user already exists")