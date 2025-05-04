from sqlalchemy import create_engine, text
import pandas as pd
import os

def connect_to_database():
    print("\n=== Database Connection ===")
    try:
        engine = create_engine('sqlite:///queue.db')
        print("✓ Successfully connected to database")
        return engine
    except Exception as e:
        print(f"✗ Connection failed: {str(e)}")
        return None

def get_all_tables(engine):
    print("\n=== Getting Table Names ===")
    try:
        query = text("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in engine.execute(query)]
        print(f"✓ Found {len(tables)} tables: {', '.join(tables)}")
        return tables
    except Exception as e:
        print(f"✗ Error getting tables: {str(e)}")
        return []

def display_table_contents(engine, table_name):
    print(f"\n=== Contents of {table_name} table ===")
    try:
        # Get column names
        columns_query = text(f"PRAGMA table_info('{table_name}')")
        columns = [row[1] for row in engine.execute(columns_query)]
        print("\nColumns:", ", ".join(columns))
        
        # Get all data
        query = text(f"SELECT * FROM {table_name}")
        results = engine.execute(query)
        
        # Convert to pandas DataFrame for better display
        df = pd.DataFrame(results, columns=columns)
        
        if len(df) > 0:
            print(f"\nTotal rows: {len(df)}")
            print("\nData Preview:")
            # Set display options for better readability
            pd.set_option('display.max_columns', None)
            pd.set_option('display.max_rows', None)
            pd.set_option('display.width', None)
            print(df)
        else:
            print("Table is empty")
            
    except Exception as e:
        print(f"✗ Error displaying table contents: {str(e)}")

def main():
    print("=== Database Contents Viewer ===")
    
    # Check if database exists
    if not os.path.exists("queue.db"):
        print("✗ Database file not found!")
        return
    
    # Connect to database
    engine = connect_to_database()
    if not engine:
        return
    
    # Get all tables
    tables = get_all_tables(engine)
    if not tables:
        return
    
    # Display contents of each table
    for table in tables:
        display_table_contents(engine, table)
    
    print("\n=== Summary ===")
    print("✓ Database contents retrieved successfully")
    print("If you need to export this data, you can add export functionality.")

if __name__ == "__main__":
    main() 