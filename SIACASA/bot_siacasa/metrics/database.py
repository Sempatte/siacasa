# bot_siacasa/metrics/database.py
from sqlalchemy import create_engine, Column, String, Float, Integer, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.sql import func
import uuid
from datetime import datetime
from typing import Generator
import os
from dotenv import load_dotenv

load_dotenv()

# Configuración de base de datos
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/siacasa_db")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Modelos de Base de Datos
class DBSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    cliente_type = Column(String(50), nullable=True)
    start_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    end_time = Column(DateTime, nullable=True)
    initial_sentiment = Column(String(20), nullable=False)
    final_sentiment = Column(String(20), nullable=True)
    resolution_status = Column(String(20), nullable=True)
    total_messages = Column(Integer, default=0)
    escalation_required = Column(Boolean, default=False)
    satisfaction_score = Column(Integer, nullable=True)
    
    # Métricas específicas SIACASA
    sentiment_journey = Column(JSON, nullable=True)  # Lista de sentimientos
    emotion_improvement = Column(Boolean, default=False)
    queries_resolved = Column(Integer, default=0)
    banking_services_used = Column(JSON, nullable=True)  # Lista de servicios bancarios utilizados
    avg_response_time_ms = Column(Float, default=0)
    session_duration_seconds = Column(Float, default=0)
    
    # Relación con mensajes
    messages = relationship("DBMessage", back_populates="session")

class DBMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey('chat_sessions.id'), nullable=False, index=True)
    user_message = Column(Text, nullable=False)
    bot_response = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Métricas del mensaje
    sentiment = Column(String(20), nullable=False)
    sentiment_confidence = Column(Float, default=0.0)
    intent = Column(String(100), nullable=True)
    intent_confidence = Column(Float, default=0.0)
    processing_time_ms = Column(Float, default=0.0)
    token_count = Column(Integer, default=0)
    
    # Análisis avanzado
    detected_entities = Column(JSON, nullable=True)
    is_escalation_request = Column(Boolean, default=False)
    response_tone = Column(String(20), nullable=True)
    banking_service_category = Column(String(50), nullable=True)
    
    # Relación con sesión
    session = relationship("DBSession", back_populates="messages")

class DBDailyMetrics(Base):
    __tablename__ = "daily_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date = Column(DateTime, nullable=False, unique=True, index=True)
    
    # Métricas básicas
    total_sessions = Column(Integer, default=0)
    total_messages = Column(Integer, default=0)
    avg_messages_per_session = Column(Float, default=0)
    avg_session_duration_seconds = Column(Float, default=0)
    avg_response_time_ms = Column(Float, default=0)
    
    # Métricas de efectividad
    resolution_rate = Column(Float, default=0)
    escalation_rate = Column(Float, default=0)
    sentiment_improvement_rate = Column(Float, default=0)
    avg_satisfaction_score = Column(Float, nullable=True)
    
    # Distribuciones (JSON)
    intent_distribution = Column(JSON, nullable=True)
    sentiment_distribution = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

# Funciones de utilidad
def get_database_session() -> Generator[Session, None, None]:
    """Generador de sesiones de base de datos"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_database():
    """Inicializar todas las tablas"""
    Base.metadata.create_all(bind=engine)

def reset_database():
    """Reiniciar todas las tablas (solo para desarrollo)"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

# Funciones de consulta comunes
def get_session_by_id(db: Session, session_id: str) -> DBSession:
    """Obtener sesión por ID"""
    return db.query(DBSession).filter(DBSession.id == session_id).first()

def get_user_sessions(db: Session, user_id: str, limit: int = 10) -> list[DBSession]:
    """Obtener sesiones de un usuario"""
    return db.query(DBSession).filter(
        DBSession.user_id == user_id
    ).order_by(DBSession.start_time.desc()).limit(limit).all()

def get_messages_by_session(db: Session, session_id: str) -> list[DBMessage]:
    """Obtener mensajes de una sesión"""
    return db.query(DBMessage).filter(
        DBMessage.session_id == session_id
    ).order_by(DBMessage.timestamp).all()