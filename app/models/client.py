from app import db
from datetime import datetime

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    service_type = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(20), default='waiting')
    position = db.Column(db.Integer, nullable=False)
    wait_time = db.Column(db.Integer)
    check_in_time = db.Column(db.DateTime, default=datetime.utcnow)
    called_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # Foreign keys
    agent_id = db.Column(db.Integer, db.ForeignKey('agent.id'))
    window_name = db.Column(db.String(64), nullable=False) 