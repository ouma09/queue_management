from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from database import SessionLocal, engine, Base
from models import Agent, Client
from werkzeug.security import check_password_hash
from datetime import datetime
from flask_socketio import SocketIO, emit
from functools import wraps
import os

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key')

# Initialize SocketIO with gevent
socketio = SocketIO(app, 
                   cors_allowed_origins="*",
                   async_mode='gevent')

# Create all tables
Base.metadata.create_all(bind=engine)

# Login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'agent_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        db = SessionLocal()
        try:
            agent = db.query(Agent).filter(Agent.username == username).first()
            
            if agent and check_password_hash(agent.password, password):
                session['agent_id'] = agent.id
                session['agent_name'] = agent.full_name
                session['window_name'] = agent.window_name
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', error="Invalid credentials")
        finally:
            db.close()
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/queue')
@login_required
def get_queue():
    window_name = session.get('window_name')
    db = SessionLocal()
    
    try:
        clients = db.query(Client).filter(
            Client.status.in_(['waiting', 'called']),
            Client.assigned_window == window_name
        ).order_by(Client.position).all()
        
        return jsonify([{
            'id': c.id,
            'name': c.name,
            'phone_number': c.phone_number,
            'service_type': c.service_type,
            'position': c.position,
            'wait_time': c.wait_time,
            'status': c.status
        } for c in clients])
    finally:
        db.close()

@app.route('/api/call_client/<int:client_id>', methods=['POST'])
@login_required
def call_client(client_id):
    db = SessionLocal()
    try:
        # Vérifier s'il y a déjà un client en cours d'appel ou en service
        window_name = session.get('window_name')
        active_client = db.query(Client).filter(
            Client.assigned_window == window_name,
            Client.status.in_(['called', 'in_service'])
        ).first()
        
        if active_client:
            return jsonify({
                'success': False,
                'message': f'Impossible d\'appeler un nouveau client. Le client #{active_client.id} est actuellement {active_client.status}.'
            })
        
        # Si aucun client actif, procéder à l'appel du nouveau client
        client = db.query(Client).filter(Client.id == client_id).first()
        
        if not client:
            return jsonify({'success': False, 'message': 'Client non trouvé'})
        
        # Vérifier que le client appartient à cette fenêtre
        if client.assigned_window != window_name:
            return jsonify({
                'success': False,
                'message': 'Le client est assigné à une autre fenêtre'
            })
        
        # Mettre à jour le statut du client
        client.status = 'called'
        client.called_at = datetime.now()
        client.agent_id = session.get('agent_id')
        
        # Préparer le message de notification
        notification_message = (
            f"🔔 C'est votre tour!\n"
            f"Veuillez vous présenter au {client.assigned_window} pour votre service {client.service_type}.\n"
            f"Merci de votre patience."
        )
        
        # Émettre les événements WebSocket
        socketio.emit('queue_update', {
            'action': 'client_called',
            'client_id': client.id,
            'window_name': client.assigned_window,
            'message': notification_message
        })
        
        db.commit()
        return jsonify({
            'success': True,
            'message': 'Client appelé avec succès'
        })
        
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        db.close()

@app.route('/api/complete_service/<int:client_id>', methods=['POST'])
@login_required
def complete_service(client_id):
    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.id == client_id).first()
        
        if not client:
            return jsonify({'success': False, 'message': 'Client not found'})
        
        client.status = 'completed'
        client.service_end_time = datetime.now()
        db.commit()
        
        # Update positions for waiting clients
        update_positions(db, client.assigned_window)
        
        # Emit WebSocket event
        socketio.emit('queue_update')
        
        return jsonify({'success': True, 'message': 'Service completed successfully'})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        db.close()

@app.route('/api/cancel_service/<int:client_id>', methods=['POST'])
@login_required
def cancel_service(client_id):
    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.id == client_id).first()
        
        if not client:
            return jsonify({'success': False, 'message': 'Client not found'})
        
        if client.status not in ['called', 'in_service']:
            return jsonify({'success': False, 'message': 'Can only cancel called or in-service clients'})
        
        # Reset client status
        client.status = 'waiting'
        client.called_at = None
        client.agent_id = None
        
        db.commit()
        
        # Emit WebSocket event
        socketio.emit('queue_update', {
            'action': 'service_cancelled',
            'client_id': client.id,
            'window_name': client.assigned_window
        })
        
        return jsonify({'success': True, 'message': 'Service cancelled successfully'})
        
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        db.close()

def update_positions(db, window_name):
    """Update positions for waiting clients"""
    clients = db.query(Client).filter(
        Client.status == 'waiting',
        Client.assigned_window == window_name
    ).order_by(Client.check_in_time).all()
    
    for i, client in enumerate(clients, 1):
        client.position = i
        client.wait_time = max(1, client.wait_time - 5)  # Reduce wait time
    
    db.commit()

# Socket.IO events
@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False) 