from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Date, Float, ForeignKey
from sqlalchemy.sql import func
from database import Base
from datetime import datetime

class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(200), nullable=False)
    full_name = Column(String(100), nullable=False)
    window_name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=False)
    service_type = Column(String(100), nullable=False)
    status = Column(String(20), default='waiting')
    position = Column(Integer, nullable=False)
    wait_time = Column(Integer)
    check_in_time = Column(DateTime, default=datetime.now)
    called_at = Column(DateTime, nullable=True)
    service_end_time = Column(DateTime, nullable=True)
    assigned_window = Column(String(100), nullable=False)
    agent_id = Column(Integer, ForeignKey('agents.id'), nullable=True)

class ServiceType(Base):
    __tablename__ = "service_types"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    average_duration = Column(Integer)  # in minutes
    assigned_window = Column(String(100), nullable=False)

class QueueStats(Base):
    __tablename__ = "queue_stats"

    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    total_clients = Column(Integer, default=0)
    total_wait_time = Column(Integer, default=0)  # in minutes
    total_service_time = Column(Integer, default=0)  # in minutes
    average_wait_time = Column(Float, default=0)
    average_service_time = Column(Float, default=0)
    peak_wait_time = Column(Integer, default=0)  # in minutes
    peak_queue_length = Column(Integer, default=0)

class QueueArchive(Base):
    __tablename__ = "queue_archive"

    id = Column(Integer, primary_key=True)
    service_type = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False)
    position = Column(Integer, nullable=False)
    wait_time = Column(Integer)
    created_at = Column(DateTime)
    called_at = Column(DateTime)
    completed_at = Column(DateTime)
    agent_id = Column(Integer)
    phone_number = Column(String(20))
    window_name = Column(String(100))
    archive_date = Column(DateTime, default=func.now()) 