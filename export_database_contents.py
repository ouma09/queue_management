from sqlalchemy import create_engine, text
import pandas as pd
import os
from datetime import datetime

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

def export_table_contents(engine, table_name, export_dir):
    print(f"\n=== Exporting {table_name} table ===")
    try:
        # Get all data
        query = text(f"SELECT * FROM {table_name}")
        df = pd.read_sql_query(query, engine)
        
        # Create export directory if it doesn't exist
        os.makedirs(export_dir, exist_ok=True)
        
        # Export to CSV
        csv_path = os.path.join(export_dir, f"{table_name}.csv")
        df.to_csv(csv_path, index=False)
        print(f"✓ Exported to {csv_path}")
        
        # Export to Excel
        excel_path = os.path.join(export_dir, f"{table_name}.xlsx")
        df.to_excel(excel_path, index=False)
        print(f"✓ Exported to {excel_path}")
        
        # Display summary
        print(f"Total rows: {len(df)}")
        print("Columns:", ", ".join(df.columns))
        
        return df
        
    except Exception as e:
        print(f"✗ Error exporting table contents: {str(e)}")
        return None

def main():
    print("=== Database Contents Exporter ===")
    
    # Check if database exists
    if not os.path.exists("queue.db"):
        print("✗ Database file not found!")
        return
    
    # Create export directory with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_dir = f"database_export_{timestamp}"
    
    # Connect to database
    engine = connect_to_database()
    if not engine:
        return
    
    # Get all tables
    tables = get_all_tables(engine)
    if not tables:
        return
    
    # Export contents of each table
    all_data = {}
    for table in tables:
        df = export_table_contents(engine, table, export_dir)
        if df is not None:
            all_data[table] = df
    
    # Create a summary report
    with open(os.path.join(export_dir, "summary_report.txt"), "w") as f:
        f.write("Database Export Summary\n")
        f.write(f"Generated on: {datetime.now()}\n\n")
        
        for table, df in all_data.items():
            f.write(f"\nTable: {table}\n")
            f.write(f"Number of records: {len(df)}\n")
            f.write(f"Columns: {', '.join(df.columns)}\n")
            f.write("-" * 50 + "\n")
    
    print(f"\n=== Export Complete ===")
    print(f"✓ All data exported to directory: {export_dir}")
    print("✓ Files exported in both CSV and Excel formats")
    print("✓ Summary report generated")

if __name__ == "__main__":
    main() 