from database import engine, SessionLocal, Base
from models import Client, Agent
import sqlite3

def check_database():
    """Check database tables and schema"""
    print("Checking database...")
    
    # Check SQLite tables
    conn = sqlite3.connect("queue.db")
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"Tables in database: {tables}")
    
    # Check clients table schema
    try:
        cursor.execute("PRAGMA table_info(clients);")
        columns = cursor.fetchall()
        print("\nClient table schema:")
        for col in columns:
            print(f"  {col}")
    except Exception as e:
        print(f"Error checking clients table: {str(e)}")
    
    # Check for integrity issues
    try:
        cursor.execute("PRAGMA integrity_check;")
        integrity = cursor.fetchall()
        print(f"\nIntegrity check: {integrity}")
    except Exception as e:
        print(f"Error checking integrity: {str(e)}")
    
    # Check for foreign key issues
    try:
        cursor.execute("PRAGMA foreign_key_check;")
        fk_issues = cursor.fetchall()
        print(f"Foreign key issues: {fk_issues}")
    except Exception as e:
        print(f"Error checking foreign keys: {str(e)}")
    
    conn.close()
    
    # Now check SQLAlchemy models
    db = SessionLocal()
    try:
        # Check Client model
        print("\nChecking Client model...")
        clients_count = db.query(Client).count()
        print(f"Total clients in database: {clients_count}")
        
        # Check Agent model
        print("\nChecking Agent model...")
        agents_count = db.query(Agent).count()
        print(f"Total agents in database: {agents_count}")
        
    except Exception as e:
        print(f"Error checking models: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    check_database() 