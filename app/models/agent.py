from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class Agent(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    full_name = db.Column(db.String(128), nullable=False)
    window_name = db.Column(db.String(64), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    clients = db.relationship('Client', backref='agent', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password) 