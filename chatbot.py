from flask import Flask, request, jsonify, render_template
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests
from flask_socketio import SocketIO, emit
from database import SessionLocal
from models import Client, ServiceType, QueueStats
from sqlalchemy import func
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)
socketio = SocketIO(app, 
                   cors_allowed_origins="*",
                   async_mode='threading',
                   ping_timeout=60,
                   ping_interval=25,
                   logger=True,
                   engineio_logger=True)

# Document requirements for each service
DOCUMENT_REQUIREMENTS = {
    'Loan Application': [
        'ID Card',
        'Proof of Income',
        'Bank Statements (last 3 months)',
        'Property Documents (if applicable)'
    ],
    'Account Opening': [
        'ID Card',
        'Proof of Address',
        'Initial Deposit'
    ],
    'General Inquiry': [
        'ID Card'
    ]
}

# Service descriptions and window mappings
SERVICE_DESCRIPTIONS = {
    'Loan Application': 'Loan services include personal loans, home loans, and business loans.',
    'Account Opening': 'Account services include opening new accounts, account modifications, and account closures.',
    'General Inquiry': 'General inquiries about bank services, fees, and policies.'
}

# Map service types to windows
SERVICE_WINDOW_MAP = {
    'Loan Application': 'Guichet Prêt',
    'Account Opening': 'Guichet Compte',
    'General Inquiry': 'Guichet Compte'
}

# Base wait times for each service type (in minutes)
BASE_WAIT_TIMES = {
    'Loan Application': 30,
    'Account Opening': 15,
    'General Inquiry': 10
}

# User session management
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

def add_to_queue(phone_number, service_type):
    print("\n=== Adding Client to Queue ===")
    print(f"Phone: {phone_number}")
    print(f"Service: {service_type}")
    
    try:
        # Verify database connection
        db = SessionLocal()
        print("Database connection established")
        
        # Verify service type exists
        if service_type not in SERVICE_DESCRIPTIONS:
            print(f"Invalid service type: {service_type}")
            return None, None, None
        
        # Get session name for the client
        user_session = get_user_session(phone_number)
        client_name = user_session.get('name', 'Chat Client') if user_session else 'Chat Client'
        
        # Get window information
        window_name = SERVICE_WINDOW_MAP.get(service_type)
        print(f"Window name: {window_name}")
        
        try:
            # Get current max position for this service type
            max_position = db.query(Client).filter(
                Client.status == "waiting",
                Client.assigned_window == window_name
            ).count() + 1
            print(f"New position: {max_position}")
            
            # Calculate wait time
            base_wait_time = BASE_WAIT_TIMES.get(service_type, 15)
            wait_time = base_wait_time * max_position
            print(f"Calculated wait time: {wait_time} minutes")
            
            # Create client object with all required fields
            try:
                new_client = Client(
                    name=client_name,
                    phone_number=phone_number,
                    service_type=service_type,
                    status="waiting",
                    position=max_position,
                    wait_time=wait_time,
                    assigned_window=window_name,
                    check_in_time=datetime.now()
                )
                
                print("Created client object")
                
                # Add to database
                db.add(new_client)
                db.commit()
                
                print(f"Client added to database")
                db.refresh(new_client)
                print(f"Client ID: {new_client.id}")
                
                return new_client.id, max_position, wait_time
                
            except Exception as e:
                print(f"Error creating client object: {str(e)}")
                import traceback
                print(traceback.format_exc())
                db.rollback()
                return None, None, None
                
        except Exception as e:
            print(f"Error calculating position or wait time: {str(e)}")
            import traceback
            print(traceback.format_exc())
            db.rollback()
            return None, None, None
            
    except Exception as e:
        print(f"Database connection error: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return None, None, None
    finally:
        try:
            db.close()
            print("Database connection closed")
        except Exception as e:
            print(f"Error closing database: {str(e)}")
        print("=== End of Add to Queue ===\n")

#@app.route('/')
#def chat_interface():
   # return render_template('chat_test.html')

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    print("\n=== Webhook Called ===")
    
    if request.method == 'GET':
        print("GET request received - handling verification")
        return request.args.get('hub.challenge', '')
    
    # Get the message from the request
    message = request.form.get('Body', '').strip()
    from_number = request.form.get('From', '')
    
    print(f"Received message from {from_number}: {message}")
    
    # Ensure we have valid data
    if not from_number:
        print("No phone number provided")
        return jsonify({
            'message': "Sorry, there was an error processing your request.",
            'status': 'error'
        })
    
    # Initialize or get user session
    if not message or message.lower() == 'start':
        create_user_session(from_number)
        response_message = "Hello! I'm the bot from Queue Management. What is your name?"
        update_user_session(from_number, {'step': 'get_name'})
        return jsonify({
            'message': response_message,
            'status': 'success'
        })
    
    session = get_user_session(from_number)
    if not session:
        print("No session found, creating new session")
        create_user_session(from_number)
        response_message = "Hello! I'm the bot from Queue Management. What is your name?"
        update_user_session(from_number, {'step': 'get_name'})
        return jsonify({
            'message': response_message,
            'status': 'success'
        })
    
    print(f"Current session state: {session}")
    
    # Handle the conversation flow
    if session['step'] == 'get_name':
        update_user_session(from_number, {'name': message})
        service_options = "\n".join([f"{i+1}. {service}" for i, service in enumerate(SERVICE_DESCRIPTIONS.keys())])
        response_message = f"Nice to meet you {message}! Please select your service type by number:\n{service_options}"
        update_user_session(from_number, {'step': 'get_service'})
    
    elif session['step'] == 'get_service':
        try:
            service_index = int(message) - 1
            if service_index < 0 or service_index >= len(SERVICE_DESCRIPTIONS):
                raise ValueError("Invalid service index")
                
            service_type = list(SERVICE_DESCRIPTIONS.keys())[service_index]
            update_user_session(from_number, {'service_type': service_type})
            
            # Get document requirements for the selected service
            documents = DOCUMENT_REQUIREMENTS[service_type]
            document_list = "\n".join([f"- {doc}" for doc in documents])
            
            # Get window information
            window_name = SERVICE_WINDOW_MAP.get(service_type)
            
            response_message = (
                f"You selected {service_type}.\n\n"
                f"Required documents:\n{document_list}\n\n"
                f"You will be served at: {window_name}\n\n"
                "Do you have all these documents with you? (yes/no)"
            )
            update_user_session(from_number, {'step': 'check_documents'})
        except (ValueError, IndexError) as e:
            print(f"Invalid service selection: {str(e)}")
            response_message = "Please enter a valid number from the list."
    
    elif session['step'] == 'check_documents':
        if message.lower() in ['yes', 'y']:
            update_user_session(from_number, {'has_documents': True})
            
            # Fallback option: Create client directly
            try:
                db = SessionLocal()
                service_type = session['service_type']
                window_name = SERVICE_WINDOW_MAP.get(service_type)
                
                # Get current max position
                max_position = db.query(Client).filter(
                    Client.status == "waiting",
                    Client.assigned_window == window_name
                ).count() + 1
                
                # Calculate wait time
                base_wait_time = BASE_WAIT_TIMES.get(service_type, 15)
                wait_time = base_wait_time * max_position
                
                # Create new client
                new_client = Client(
                    name=session.get('name', 'Chat Client'),
                    phone_number=from_number,
                    service_type=service_type,
                    status="waiting",
                    position=max_position,
                    wait_time=wait_time,
                    check_in_time=datetime.now(),
                    assigned_window=window_name
                )
                
                db.add(new_client)
                db.commit()
                db.refresh(new_client)
                
                print(f"Successfully created client {new_client.id} directly")
                
                # Success message
                response_message = (
                    f"Great! You've been added to the queue.\n"
                    f"Your position: {max_position}\n"
                    f"Estimated wait time: {wait_time} minutes\n"
                    f"Please proceed to: {window_name}\n\n"
                    "You will receive updates about your position in the queue."
                )
                
                # Try to emit socket event
                try:
                    socketio.emit('queue_update', {
                        'action': 'new_client',
                        'client_id': new_client.id,
                        'service_type': service_type,
                        'window_name': window_name,
                        'position': max_position,
                        'wait_time': wait_time,
                        'phone_number': from_number
                    })
                    print("Emitted WebSocket event")
                except Exception as se:
                    print(f"Socket error: {str(se)}")
                
            except Exception as e:
                print(f"Error adding client directly: {str(e)}")
                import traceback
                print(traceback.format_exc())
                db.rollback()
                response_message = "Sorry, there was an error adding you to the queue. Please try again later."
            finally:
                db.close()
            
            # Clear session regardless of success or failure
            clear_user_session(from_number)
            
        elif message.lower() in ['no', 'n']:
            response_message = (
                "Please gather all required documents and return when you have them ready.\n"
                "Type 'start' to begin again when you're ready."
            )
            clear_user_session(from_number)
        else:
            response_message = "Please answer with 'yes' or 'no'."
    
    else:
        response_message = "Type 'start' to begin the conversation."
        clear_user_session(from_number)
    
    print(f"Sending response: {response_message}")
    return jsonify({
        'message': response_message,
        'status': 'success'
    })

# Remove or update the test route to use the same template
@app.route('/test')
def test_interface():
    return render_template('chat_test.html')  # Use the same template

@app.route('/get_session')
def get_session():
    phone_number = request.args.get('phone_number', 'test_phone_number')
    session = get_user_session(phone_number)
    return jsonify(session or {})

@app.route('/get_queue_info/<int:client_id>')
def get_queue_info(client_id):
    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.id == client_id).first()
        if client:
            return jsonify({
                'position': client.position,
                'wait_time': client.wait_time
            })
        return jsonify({})
    except Exception as e:
        print(f"Error getting queue info: {str(e)}")
        return jsonify({})
    finally:
        db.close()

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5001) 