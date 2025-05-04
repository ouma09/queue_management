from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

auth = Blueprint('auth', __name__)

def get_db_connection():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'queue.db')
    return sqlite3.connect(db_path)

def init_auth_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Create agents table
    c.execute('''
        CREATE TABLE IF NOT EXISTS agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            window_name TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # Check if we need to add test agents
    c.execute('SELECT COUNT(*) FROM agents')
    if c.fetchone()[0] == 0:
        print("Adding test agents to the database...")
        # Add some test agents
        test_agents = [
            ('agent1', generate_password_hash('password1'), 'Ahmed Charki', 'Guichet Crédit'),
            ('agent2', generate_password_hash('password2'), 'Fatima Zahra', 'Guichet Compte'),
            ('agent3', generate_password_hash('password3'), 'Karim Benani', 'Guichet Prêt')
        ]
        c.executemany('''
            INSERT INTO agents (username, password, full_name, window_name)
            VALUES (?, ?, ?, ?)
        ''', test_agents)
        print("Test agents added successfully!")
    
    conn.commit()
    conn.close()

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM agents WHERE username = ?', (username,))
        agent = c.fetchone()
        conn.close()
        
        if agent and check_password_hash(agent[2], password):
            session['agent_id'] = agent[0]
            session['agent_name'] = agent[3]
            session['window_name'] = agent[4]
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@auth.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login')) 