from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from app.db import close_db

# Initialisation des extensions
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register database teardown
    app.teardown_appcontext(close_db)

    # Enregistrer les Blueprints
    from app.auth.routes import auth_bp
    from app.admin.routes import admin_bp
    from app.eleve.routes import eleve_bp
    from app.prof.routes import prof_bp
    from .parent.routes import parent_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(eleve_bp, url_prefix='/eleve')
    app.register_blueprint(prof_bp, url_prefix='/prof')
    app.register_blueprint(parent_bp, url_prefix='/parent')

    return app
