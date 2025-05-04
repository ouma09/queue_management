import sqlite3
import os

def init_db():
    # Delete existing database if it exists
    if os.path.exists('queue.db'):
        os.remove('queue.db')
        print("Deleted existing database")

    # Create new database
    conn = sqlite3.connect('queue.db')
    c = conn.cursor()
    
    # Create queue table
    c.execute('''
        CREATE TABLE IF NOT EXISTS queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_type TEXT NOT NULL,
            status TEXT NOT NULL,
            position INTEGER NOT NULL,
            wait_time INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP
        )
    ''')
    
    # Add test data
    # les donnes restent statiquent mais ils s'ajustent en fonction de chaque client (l'agent qui l'ajuste)
    test_data = [
        ('Credit Service', 'waiting', 1, 5),
        ('Account Opening', 'waiting', 2, 10),
        ('Loan Application', 'waiting', 3, 15),
        ('Card Service', 'waiting', 4, 20),
        ('General Inquiry', 'waiting', 5, 25)
    ]
    
    c.executemany('''
        INSERT INTO queue (service_type, status, position, wait_time)
        VALUES (?, ?, ?, ?)
    ''', test_data)
    
    conn.commit()
    print("Added test clients:")
    
    # Verify the data
    c.execute('SELECT id, service_type, status, position, wait_time FROM queue')
    for row in c.fetchall():
        print(f"Client {row[0]}: {row[1]} (Status: {row[2]}, Position: {row[3]}, Wait Time: {row[4]}min)")
    
    conn.close()
    print("\nDatabase reset complete!")

if __name__ == '__main__':
    init_db() 