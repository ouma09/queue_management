from database import engine, SessionLocal
from models import Base, Agent, Client
from werkzeug.security import generate_password_hash
from datetime import datetime

def reset_database():
    # Drop all tables
    Base.metadata.drop_all(bind=engine)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    db = SessionLocal()
    
    try:
        # Add test agents
        test_agents = [
            Agent(
                username='agent1',
                password=generate_password_hash('password1'),
                full_name='Ahmed Charki',
                window_name='Guichet Crédit'
            ),
            Agent(
                username='agent2',
                password=generate_password_hash('password2'),
                full_name='Fatima Zahra',
                window_name='Guichet Compte'
            ),
            Agent(
                username='agent3',
                password=generate_password_hash('password3'),
                full_name='Karim Benani',
                window_name='Guichet Prêt'
            )
        ]
        
        db.add_all(test_agents)
        db.commit()
        
        # Add test clients
        test_clients = [
            Client(
                phone_number='+212600000001',
                service_type='Credit Service',
                status='waiting',
                position=1,
                wait_time=5,
                created_at=datetime.now(),
                assigned_window='Guichet Crédit'
            ),
            Client(
                phone_number='+212600000002',
                service_type='Account Opening',
                status='waiting',
                position=2,
                wait_time=10,
                created_at=datetime.now(),
                assigned_window='Guichet Compte'
            )
        ]
        
        db.add_all(test_clients)
        db.commit()
        
        print("Database reset successful!")
        
    except Exception as e:
        print(f"Error resetting database: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reset_database() 