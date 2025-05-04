from flask import Blueprint, jsonify
from app.services import QueueService
from app.models import Client
from flask_login import login_required

queue_bp = Blueprint('queue', __name__)

@queue_bp.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Resource not found'}), 404

@queue_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@queue_bp.route('/api/queue/<window_name>')
@login_required
def get_queue(window_name):
    try:
        clients = QueueService.get_window_queue(window_name)
        return jsonify([client.to_dict() for client in clients])
    except Exception as e:
        return jsonify({'error': str(e)}), 500 