from datetime import datetime, timedelta
from models import db, Client, ServiceType, QueueStats
from config import Config

class QueueService:
    @staticmethod
    def add_client(phone_number, service_type):
        """Add a new client to the queue"""
        # Get the assigned window for the service type
        assigned_window = Config.SERVICE_WINDOWS.get(service_type, "Guichet Divers")
        
        # Get the current position (last position + 1)
        last_client = Client.query.order_by(Client.position.desc()).first()
        new_position = 1 if not last_client else last_client.position + 1
        
        # Create new client
        client = Client(
            phone_number=phone_number,
            position=new_position,
            service_type=service_type,
            assigned_window=assigned_window,
            status='waiting',
            check_in_time=datetime.utcnow()
        )
        
        db.session.add(client)
        db.session.commit()
        return client

    @staticmethod
    def get_next_client(window):
        """Get the next client for a specific window"""
        return Client.query.filter_by(
            assigned_window=window,
            status='waiting'
        ).order_by(Client.position).first()

    @staticmethod
    def start_service(client_id):
        """Start serving a client"""
        client = Client.query.get_or_404(client_id)
        client.status = 'serving'
        client.service_start_time = datetime.utcnow()
        client.wait_time = int((client.service_start_time - client.check_in_time).total_seconds() / 60)
        db.session.commit()
        return client

    @staticmethod
    def complete_service(client_id):
        """Complete service for a client"""
        client = Client.query.get_or_404(client_id)
        client.status = 'completed'
        client.service_end_time = datetime.utcnow()
        client.service_time = int((client.service_end_time - client.service_start_time).total_seconds() / 60)
        
        # Update queue stats
        QueueService.update_queue_stats(client)
        
        # Remove client and update positions
        QueueService.update_positions(client.position)
        db.session.delete(client)
        db.session.commit()
        return client

    @staticmethod
    def pause_service(client_id):
        """Pause service for a client"""
        client = Client.query.get_or_404(client_id)
        client.status = 'paused'
        db.session.commit()
        return client

    @staticmethod
    def update_positions(removed_position):
        """Update positions after removing a client"""
        clients = Client.query.filter(Client.position > removed_position).all()
        for client in clients:
            client.position -= 1
        db.session.commit()

    @staticmethod
    def update_queue_stats(client):
        """Update daily queue statistics"""
        today = datetime.utcnow().date()
        stats = QueueStats.query.filter_by(date=today).first()
        
        if not stats:
            stats = QueueStats(date=today)
            db.session.add(stats)
        
        stats.total_clients += 1
        stats.total_wait_time += client.wait_time
        stats.total_service_time += client.service_time
        stats.average_wait_time = stats.total_wait_time / stats.total_clients
        stats.average_service_time = stats.total_service_time / stats.total_clients
        
        # Update peak wait time if current wait time is higher
        if client.wait_time > stats.peak_wait_time:
            stats.peak_wait_time = client.wait_time
        
        # Update peak queue length
        current_queue_length = Client.query.filter_by(status='waiting').count()
        if current_queue_length > stats.peak_queue_length:
            stats.peak_queue_length = current_queue_length
        
        db.session.commit()

    @staticmethod
    def get_queue_stats():
        """Get current queue statistics"""
        today = datetime.utcnow().date()
        stats = QueueStats.query.filter_by(date=today).first()
        
        if not stats:
            return {
                'totalWaiting': 0,
                'avgWaitTime': '0m',
                'servedToday': 0,
                'avgServiceTime': '0m'
            }
        
        return {
            'totalWaiting': Client.query.filter_by(status='waiting').count(),
            'avgWaitTime': f"{int(stats.average_wait_time)}m",
            'servedToday': stats.total_clients,
            'avgServiceTime': f"{int(stats.average_service_time)}m"
        }

    @staticmethod
    def get_queue_data():
        """Get current queue data for the dashboard"""
        waiting_clients = Client.query.filter_by(status='waiting').order_by(Client.position).all()
        
        queue_data = []
        for client in waiting_clients:
            wait_time = int((datetime.utcnow() - client.check_in_time).total_seconds() / 60)
            queue_data.append({
                'id': client.phone_number[-4:],
                'service': client.service_type,
                'waitTime': f"{wait_time}m",
                'position': client.position,
                'status': client.status
            })
        
        return queue_data 