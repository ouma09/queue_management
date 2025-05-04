from flask import Flask, request, render_template, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from models import db, Agent, Client, ServiceType, QueueStats
from services import QueueService
from config import Config
import datetime
import random

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# Create database tables
with app.app_context():
    db.create_all()
    # Initialize service types if they don't exist
    if not ServiceType.query.first():
        for service_name, window in Config.SERVICE_WINDOWS.items():
            service = ServiceType(
                name=service_name,
                assigned_window=window,
                average_duration=Config.DEFAULT_SERVICE_TIME
            )
            db.session.add(service)
        db.session.commit()

# Agent dashboard routes
@app.route("/agent")
def agent_dashboard():
    return render_template("agent_dashboard.html")

@app.route("/api/queue")
def get_queue_data():
    stats = QueueService.get_queue_stats()
    queue_data = QueueService.get_queue_data()
    return jsonify({
        **stats,
        "queue": queue_data
    })

@app.route("/api/service/complete", methods=["POST"])
def complete_service():
    data = request.json
    client_id = data.get("clientId")
    try:
        client = QueueService.complete_service(client_id)
        return jsonify({
            "success": True,
            "message": "Service completed successfully",
            "clientData": {
                "id": client.phone_number[-4:],
                "service": client.service_type,
                "waitTime": f"{client.wait_time}m",
                "serviceTime": f"{client.service_time}m"
            }
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 404

@app.route("/api/service/pause", methods=["POST"])
def pause_service():
    data = request.json
    client_id = data.get("clientId")
    try:
        client = QueueService.pause_service(client_id)
        return jsonify({
            "success": True,
            "message": "Service paused successfully"
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 404

@app.route("/api/client/call", methods=["POST"])
def call_client():
    data = request.json
    client_id = data.get("clientId")
    try:
        client = QueueService.start_service(client_id)
        return jsonify({
            "success": True,
            "message": "Client called successfully",
            "clientData": {
                "id": client.phone_number[-4:],
                "service": client.service_type,
                "waitTime": f"{client.wait_time}m"
            }
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 404

# WhatsApp bot routes
@app.route("/sms", methods=["POST"])
def sms():
    sender = request.values.get('From', '')
    incoming_msg = request.values.get('Body', '').lower().strip()
    
    resp = MessagingResponse()
    msg = resp.message()
    
    # Agent command to advance queue
    if sender in Config.AGENT_NUMBERS and incoming_msg == "/next":
        window = "Guichet Crédit"  # This should be determined by the agent's window
        next_client = QueueService.get_next_client(window)
        if not next_client:
            msg.body("Aucun client en attente.")
            return str(resp)
        
        client = QueueService.start_service(next_client.id)
        msg.body(f"Client {client.phone_number[-4:]} a été appelé.")
        return str(resp)
    
    client_registered = Client.query.filter_by(phone_number=sender).first() is not None
    
    # Initial menu for "hello", "hi", "start"
    if incoming_msg in ["hello", "hi", "start"]:
        msg.body("Bonjour, quelle est votre demande ?\n\n" + 
                "\n".join(f"{i+1}. {service}" for i, service in enumerate(Config.SERVICE_WINDOWS.keys())))
        return str(resp)
    
    # Handle service selection
    if incoming_msg.isdigit() and 1 <= int(incoming_msg) <= len(Config.SERVICE_WINDOWS):
        service_type = list(Config.SERVICE_WINDOWS.keys())[int(incoming_msg)-1]
        
        if not client_registered:
            client = QueueService.add_client(sender, service_type)
            msg.body(f"✅ Vous avez sélectionné : {service_type}\n\n"
                     f"📍 Veuillez vous diriger vers : {client.assigned_window}\n"
                     f"🔢 Votre position : #{client.position}\n"
                     f"⏱️ Temps d'attente estimé : {client.position * Config.DEFAULT_SERVICE_TIME} minutes")
        else:
            client = Client.query.filter_by(phone_number=sender).first()
            client.service_type = service_type
            client.assigned_window = Config.SERVICE_WINDOWS[service_type]
            db.session.commit()
            msg.body(f"Votre demande a été mise à jour en : {service_type}\n\n"
                     f"📍 Veuillez vous diriger vers : {client.assigned_window}\n"
                     f"🔢 Votre position : #{client.position}\n"
                     f"⏱️ Temps d'attente estimé : {client.position * Config.DEFAULT_SERVICE_TIME} minutes")
        return str(resp)
    
    # Handle status request
    if "status" in incoming_msg or "position" in incoming_msg:
        if client_registered:
            client = Client.query.filter_by(phone_number=sender).first()
            wait_time = int((datetime.datetime.utcnow() - client.check_in_time).total_seconds() / 60)
            msg.body(f"🔢 Statut actuel :\n\n"
                     f"📍 Dirigez-vous vers : {client.assigned_window}\n"
                     f"🔢 Votre position : #{client.position}\n"
                     f"⏱️ Temps d'attente estimé : {client.position * Config.DEFAULT_SERVICE_TIME} minutes\n"
                     f"⏰ Heure d'enregistrement : {client.check_in_time.strftime('%H:%M')}")
        else:
            msg.body("Bonjour, quelle est votre demande ?\n\n" + 
                     "\n".join(f"{i+1}. {service}" for i, service in enumerate(Config.SERVICE_WINDOWS.keys())))
        return str(resp)
    
    # Default response
    if client_registered:
        client = Client.query.filter_by(phone_number=sender).first()
        msg.body(f"Votre statut actuel :\n\n"
                 f"📍 Dirigez-vous vers : {client.assigned_window}\n"
                 f"🔢 Votre position : #{client.position}\n"
                 f"⏱️ Temps d'attente estimé : {client.position * Config.DEFAULT_SERVICE_TIME} minutes")
    else:
        msg.body("Bonjour, quelle est votre demande ?\n\n" + 
                 "\n".join(f"{i+1}. {service}" for i, service in enumerate(Config.SERVICE_WINDOWS.keys())))
    
    return str(resp)

# Test interface route
@app.route("/test", methods=["GET", "POST"])
def test():
    user_message = ""
    bot_response = ""
    
    if request.method == "POST":
        user_message = request.form.get("message", "").lower().strip()
        
        class FakeRequest:
            def __init__(self, message):
                self.values = {"Body": message, "From": "+123456789"}
                
            def get(self, key, default=""):
                return self.values.get(key, default)
        
        resp = MessagingResponse()
        request.values = FakeRequest(user_message).values
        response_xml = sms()
        
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response_xml)
        body_element = root.find(".//Body")
        if body_element is not None:
            bot_response = body_element.text
    
    return f"""
    <html>
    <head>
        <title>Bank Queue Bot</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .chat-container {{ max-width: 600px; margin: 0 auto; }}
            .message {{ padding: 10px; margin: 10px 0; border-radius: 10px; }}
            .user-message {{ background-color: #DCF8C6; text-align: right; }}
            .bot-message {{ background-color: #F1F0F0; }}
            input[type=text] {{ width: 80%; padding: 10px; }}
            input[type=submit] {{ padding: 10px; }}
        </style>
    </head>
    <body>
        <div class="chat-container">
            <h1>Bank Queue Bot</h1>
            
            {f'<div class="message user-message"><strong>You:</strong> {user_message}</div>' if user_message else ''}
            {f'<div class="message bot-message"><strong>Bot:</strong> {bot_response}</div>' if bot_response else ''}
            
            <form method="post" action="/test">
                <input type="text" name="message" placeholder="Tapez votre message..." required>
                <input type="submit" value="Envoyer">
            </form>
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    app.run(debug=True)
