import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# First, let's check if the database file exists
def check_database_file():
    print("\n=== Checking Database File ===")
    db_path = "queue.db"  # Update this path if your database is located elsewhere
    if os.path.exists(db_path):
        print(f"✓ Database file found at: {db_path}")
        print(f"✓ File size: {os.path.getsize(db_path) / 1024:.2f} KB")
    else:
        print(f"✗ Database file not found at: {db_path}")
        return False
    return True

# Test database connection
def test_connection():
    print("\n=== Testing Database Connection ===")
    try:
        # Create engine
        engine = create_engine('sqlite:///queue.db', echo=False)
        
        # Test connection
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("✓ Successfully connected to database")
            return engine
    except SQLAlchemyError as e:
        print(f"✗ Failed to connect to database: {str(e)}")
        return None

# Check database tables
def check_tables(engine):
    print("\n=== Checking Database Tables ===")
    try:
        with engine.connect() as connection:
            # Get all tables
            result = connection.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' 
                ORDER BY name;
            """))
            tables = result.fetchall()
            
            if tables:
                print("Found tables:")
                for table in tables:
                    print(f"  - {table[0]}")
                    # Get table structure
                    columns = connection.execute(text(f"PRAGMA table_info('{table[0]}')"))
                    print("    Columns:")
                    for col in columns:
                        print(f"      {col[1]} ({col[2]})")
            else:
                print("✗ No tables found in database")
            
            return bool(tables)
    except SQLAlchemyError as e:
        print(f"✗ Error checking tables: {str(e)}")
        return False

# Test basic CRUD operations
def test_crud_operations(engine):
    print("\n=== Testing CRUD Operations ===")
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Test SELECT
        print("\nTesting SELECT operation:")
        result = session.execute(text("SELECT COUNT(*) FROM clients"))
        count = result.scalar()
        print(f"✓ Found {count} clients in database")

        # Test SELECT on agents
        print("\nTesting SELECT on agents table:")
        result = session.execute(text("SELECT COUNT(*) FROM agents"))
        count = result.scalar()
        print(f"✓ Found {count} agents in database")

        # Show sample data
        print("\nSample client data:")
        clients = session.execute(text("SELECT * FROM clients LIMIT 10"))
        for client in clients:
            print(f"  Client ID: {client[0]}")
            print(f"  Name: {client[1]}")
            print(f"  Service: {client[3]}")
            print(f"  Status: {client[4]}")
            print(f"  Created At: {client[5]}")
            print(f"  Updated At: {client[6]}")
            print(f"  Phone: {client[7]}")
            print(f"  Email: {client[8]}")
            print(f"  Address: {client[9]}")
            print(f"  City: {client[10]}")
            print(f"  State: {client[11]}")
            print(f"  Zip: {client[12]}")
            print("  ---")

        return True

    except SQLAlchemyError as e:
        print(f"✗ Error during CRUD operations: {str(e)}")
        return False
    finally:
        session.close()

# Check database integrity
def check_integrity(engine):
    print("\n=== Checking Database Integrity ===")
    try:
        with engine.connect() as connection:
            # Run SQLite integrity check
            result = connection.execute(text("PRAGMA integrity_check"))
            integrity = result.scalar()
            print(f"Integrity check result: {integrity}")

            # Check foreign keys
            result = connection.execute(text("PRAGMA foreign_key_check"))
            fk_violations = result.fetchall()
            if not fk_violations:
                print("✓ No foreign key violations found")
            else:
                print(f"✗ Found {len(fk_violations)} foreign key violations")

            return integrity == 'ok' and not fk_violations
    except SQLAlchemyError as e:
        print(f"✗ Error checking integrity: {str(e)}")
        return False

def main():
    print("=== Database Connection Test Script ===")
    print(f"Running tests at: {datetime.now()}")
    
    # Step 1: Check if database file exists
    if not check_database_file():
        print("\n❌ Critical Error: Database file not found!")
        sys.exit(1)

    # Step 2: Test connection
    engine = test_connection()
    if not engine:
        print("\n❌ Critical Error: Could not connect to database!")
        sys.exit(1)

    # Step 3: Check tables
    if not check_tables(engine):
        print("\n⚠️ Warning: Issues found with database tables!")
    
    # Step 4: Test CRUD operations
    if not test_crud_operations(engine):
        print("\n⚠️ Warning: Issues found with CRUD operations!")

    # Step 5: Check database integrity
    if not check_integrity(engine):
        print("\n⚠️ Warning: Issues found with database integrity!")

    print("\n=== Test Summary ===")
    print("✓ Database file check completed")
    print("✓ Connection test completed")
    print("✓ Table structure check completed")
    print("✓ CRUD operations test completed")
    print("✓ Integrity check completed")
    print("\nIf you see any warnings or errors above, please address them before proceeding.")

if __name__ == "__main__":
    main() 