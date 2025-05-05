# app.py (merged Flask + chatbot app)

from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from database import SessionLocal, engine, Base
from models import Agent, Client, ServiceType, QueueStats
from werkzeug.security import check_password_hash
from datetime import datetime
from flask_socketio import SocketIO, emit
from functools import wraps
from sqlalchemy import func
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key')

# Initialize SocketIO with gevent
socketio = SocketIO(app,
                    cors_allowed_origins="*",
                    async_mode='gevent',
                    ping_timeout=60,
                    ping_interval=25,
                    logger=True,
                    engineio_logger=True)

# Create all tables
Base.metadata.create_all(bind=engine)

# Chatbot service data
DOCUMENT_REQUIREMENTS = {
    'Loan Application': ['ID Card', 'Proof of Income', 'Bank Statements (last 3 months)', 'Property Documents (if applicable)'],
    'Account Opening': ['ID Card', 'Proof of Address', 'Initial Deposit'],
    'General Inquiry': ['ID Card']
}

SERVICE_DESCRIPTIONS = {
    'Loan Application': 'Loan services include personal loans, home loans, and business loans.',
    'Account Opening': 'Account services include opening new accounts, account modifications, and account closures.',
    'General Inquiry': 'General inquiries about bank services, fees, and policies.'
}

SERVICE_WINDOW_MAP = {
    'Loan Application': 'Guichet Prêt',
    'Account Opening': 'Guichet Compte',
    'General Inquiry': 'Guichet Compte'
}

BASE_WAIT_TIMES = {
    'Loan Application': 30,
    'Account Opening': 15,
    'General Inquiry': 10
}

user_sessions = {}

def create_user_session(phone_number):
    user_sessions[phone_number] = {
        'step': 'welcome',
        'name': None,
        'service_type': None,
        'documents': [],
        'has_documents': None
    }

def update_user_session(phone_number, updates):
    if phone_number in user_sessions:
        user_sessions[phone_number].update(updates)

def get_user_session(phone_number):
    return user_sessions.get(phone_number)

def clear_user_session(phone_number):
    if phone_number in user_sessions:
        del user_sessions[phone_number]

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
        window_name = session.get('window_name')
        active_client = db.query(Client).filter(
            Client.assigned_window == window_name,
            Client.status.in_(['called', 'in_service'])
        ).first()

        if active_client:
            return jsonify({'success': False, 'message': f'Client #{active_client.id} is currently {active_client.status}.'})

        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            return jsonify({'success': False, 'message': 'Client not found'})
        if client.assigned_window != window_name:
            return jsonify({'success': False, 'message': 'Client is assigned to another window'})

        client.status = 'called'
        client.called_at = datetime.now()
        client.agent_id = session.get('agent_id')

        notification_message = (
            f"\ud83d\udd14 C'est votre tour!\n"
            f"Veuillez vous présenter au {client.assigned_window} pour votre service {client.service_type}.\n"
            f"Merci de votre patience."
        )

        socketio.emit('queue_update', {
            'action': 'client_called',
            'client_id': client.id,
            'window_name': client.assigned_window,
            'message': notification_message
        })

        db.commit()
        return jsonify({'success': True, 'message': 'Client called successfully'})
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

        update_positions(db, client.assigned_window)
        socketio.emit('queue_update')
        return jsonify({'success': True, 'message': 'Service completed'})
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

        client.status = 'waiting'
        client.called_at = None
        client.agent_id = None
        db.commit()

        socketio.emit('queue_update', {
            'action': 'service_cancelled',
            'client_id': client.id,
            'window_name': client.assigned_window
        })

        return jsonify({'success': True, 'message': 'Service cancelled'})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        db.close()

def update_positions(db, window_name):
    clients = db.query(Client).filter(
        Client.status == 'waiting',
        Client.assigned_window == window_name
    ).order_by(Client.check_in_time).all()

    for i, client in enumerate(clients, 1):
        client.position = i
        client.wait_time = max(1, client.wait_time - 5)

    db.commit()

# Chatbot endpoints copied below (e.g., /webhook, /get_session, etc.)
# ... (Insert the chatbot routes from chatbot.py here)

@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
