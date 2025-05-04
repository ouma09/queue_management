from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_migrate import Migrate
from .config import config

db = SQLAlchemy()
socketio = SocketIO()
login_manager = LoginManager()
migrate = Migrate()

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")
    login_manager.init_app(app)
    migrate.init_app(app, db)
    
    # Set up login view
    login_manager.login_view = 'auth.login'
    
    # Register blueprints
    from .routes import auth_bp, queue_bp, agent_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(queue_bp)
    app.register_blueprint(agent_bp)
    
    return app 