from app import db
from app.models import Client, Agent
from datetime import datetime

class QueueService:
    @staticmethod
    def get_window_queue(window_name):
        return Client.query.filter_by(
            window_name=window_name,
            status='waiting'
        ).order_by(Client.position).all()
    
    @staticmethod
    def call_next_client(agent_id, window_name):
        client = Client.query.filter_by(
            window_name=window_name,
            status='waiting'
        ).order_by(Client.position).first()
        
        if client:
            client.status = 'called'
            client.called_at = datetime.utcnow()
            client.agent_id = agent_id
            db.session.commit()
            return client
        return None
    
    @staticmethod
    def complete_service(client_id):
        client = Client.query.get(client_id)
        if client:
            client.status = 'completed'
            client.completed_at = datetime.utcnow()
            db.session.commit()
            
            # Update positions
            QueueService.update_positions(client.window_name)
            return True
        return False
    
    @staticmethod
    def update_positions(window_name):
        clients = Client.query.filter_by(
            window_name=window_name,
            status='waiting'
        ).order_by(Client.check_in_time).all()
        
        for i, client in enumerate(clients, 1):
            client.position = i
        
        db.session.commit() 