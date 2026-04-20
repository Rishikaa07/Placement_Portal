from flask import Flask
from app.config import Config
from app.models import db

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize database
    db.init_app(app)
    
    # Create tables
    with app.app_context():
        db.create_all()
        create_default_admin()
    
    # Register blueprints
    from app.routes import auth_bp, admin_bp, company_bp, student_bp, main_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(company_bp)
    app.register_blueprint(student_bp)
    
    return app

def create_default_admin():
    """Create default admin if it doesn't exist"""
    from app.models import Admin
    from werkzeug.security import generate_password_hash
    
    admin_exists = Admin.query.filter_by(username='admin').first()
    if not admin_exists:
        admin = Admin(
            username='admin',
            password=generate_password_hash('admin123'),
            email='admin@placement.edu',
            name='System Administrator'
        )
        db.session.add(admin)
        db.session.commit()
        print("Default admin created: username=admin, password=admin123")
