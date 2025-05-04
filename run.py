from app import create_app, socketio
from app.models import Agent, Client

app = create_app()

if __name__ == '__main__':
    socketio.run(app, debug=True) 