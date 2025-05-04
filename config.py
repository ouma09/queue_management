import os

class Config:
    # Database configuration
    SQLALCHEMY_DATABASE_URI = 'sqlite:///queue_system.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Security configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') 
    #or 'dev-secret-key'
    
    # Twilio configuration
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')
    
    # Queue configuration
    DEFAULT_SERVICE_TIME = 5  # minutes
    MAX_QUEUE_LENGTH = 100
    REFRESH_INTERVAL = 30  # seconds
    
    # Agent configuration
    AGENT_NUMBERS = os.environ.get('AGENT_NUMBERS', '').split(',')
    
    # Service types and their assigned windows
    SERVICE_WINDOWS = {
        "Demande de crédit auto ou crédit personnel": "Guichet Crédit",
        "Demande d'attestation d'encours": "Guichet Attestation",
        "Demande de tableau d'amortissement": "Guichet Amortissement",
        "Demande de remboursement de trop-perçu": "Guichet Remboursement",
        "Réclamations": "Guichet Réclamations",
        "Demande de règlement des impayés": "Guichet Impayés",
        "Demande d'attestation de quitter le territoire": "Guichet Attestation Quitter",
        "Demandes diverses": "Guichet Divers",
        "Demande de mainlevée": "Guichet Mainlevée"
    } 