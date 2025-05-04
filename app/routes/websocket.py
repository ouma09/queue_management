from app import socketio
from flask_socketio import emit
from flask_login import current_user

@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        emit('connection_response', {'data': 'Connected'})

@socketio.on('queue_update')
def handle_queue_update():
    emit('queue_refresh', broadcast=True) 