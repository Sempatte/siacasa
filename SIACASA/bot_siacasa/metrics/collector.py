import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .database import get_database_session, DBSession, DBMessage
from .models import (
    SentimentType, IntentType, ResolutionStatus, ClienteType,
    MessageMetric, SessionMetric
)

logger = logging.getLogger(__name__)

class SIACASAMetricsCollector:
    """Recolector de métricas específico para SIACASA"""
    
    def __init__(self):
        self.active_sessions = {}
        self._setup_logging()
    
    def _setup_logging(self):
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - SIACASA_METRICS - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    async def start_session(
        self, 
        user_id: str, 
        cliente_type: str = "nuevo"
    ) -> UUID:
        """Iniciar nueva sesión de usuario"""
        
        session_generator = get_database_session()
        db = next(session_generator)
        
        try:
            # Convertir string a enum
            cliente_type_enum = ClienteType(cliente_type) if cliente_type in [e.value for e in ClienteType] else ClienteType.NUEVO
            
            session = DBSession(
                user_id=user_id,
                cliente_type=cliente_type_enum.value,
                initial_sentiment=SentimentType.NEUTRAL.value
            )
            
            db.add(session)
            db.commit()
            db.refresh(session)
            
            # Mantener en memoria para acceso rápido
            self.active_sessions[session.id] = {
                'start_time': session.start_time,
                'sentiment_journey': [SentimentType.NEUTRAL.value],
                'message_count': 0,
                'queries_resolved': 0
            }
            
            logger.info(f"SIACASA Session started: {session.id} for user: {user_id}")
            return session.id
            
        except SQLAlchemyError as e:
            logger.error(f"Error starting SIACASA session: {e}")
            db.rollback()
            raise
        finally:
            db.close()
    
    def record_message_sync(
        self,
        session_id: UUID,
        user_message: str,
        bot_response: str,
        sentiment: str,
        sentiment_confidence: float,
        intent: str,
        intent_confidence: float,
        processing_time_ms: float,
        token_count: int,
        is_escalation_request: bool = False,
        detected_entities: Optional[Dict] = None,
        response_tone: Optional[str] = None
    ) -> None:
        """Versión síncrona para registrar mensaje"""
        
        session_generator = get_database_session()
        db = next(session_generator)
        
        try:
            # Verificar que la sesión existe
            session = db.query(DBSession).filter(DBSession.id == session_id).first()
            if not session:
                # Crear sesión automáticamente si no existe
                logger.warning(f"Session {session_id} not found, creating automatically")
                session = DBSession(
                    id=session_id,
                    user_id="unknown_user",
                    cliente_type=ClienteType.NUEVO.value,
                    initial_sentiment=sentiment
                )
                db.add(session)
                db.flush()  # Para obtener el ID antes del commit
            
            # Crear registro de mensaje
            message = DBMessage(
                session_id=session_id,
                user_message=user_message,
                bot_response=bot_response,
                sentiment=sentiment,
                sentiment_confidence=sentiment_confidence,
                intent=intent,
                intent_confidence=intent_confidence,
                processing_time_ms=processing_time_ms,
                token_count=token_count,
                is_escalation_request=is_escalation_request,
                detected_entities=detected_entities,
                response_tone=response_tone
            )
            
            db.add(message)
            
            # Actualizar métricas de sesión
            session.total_messages += 1
            session.total_processing_time_ms += processing_time_ms
            session.total_tokens_used += token_count
            
            # Actualizar sentimiento inicial si es primer mensaje
            if session.total_messages == 1:
                session.initial_sentiment = sentiment
            
            # Detectar cambios de sentimiento
            if session_id in self.active_sessions:
                journey = self.active_sessions[session_id]['sentiment_journey']
                if journey[-1] != sentiment:
                    journey.append(sentiment)
                    # Actualizar en BD como JSON
                    session.sentiment_journey = journey
                
                # Detectar mejora emocional
                if (len(journey) >= 2 and 
                    journey[0] == SentimentType.NEGATIVO.value and 
                    sentiment in [SentimentType.NEUTRAL.value, SentimentType.POSITIVO.value]):
                    session.emotion_improvement = True
                
                # Contar queries resueltas
                if not is_escalation_request:
                    session.queries_resolved += 1
                    self.active_sessions[session_id]['queries_resolved'] += 1
            
            # Actualizar sentimiento final
            session.final_sentiment = sentiment
            
            # Detectar escalación
            if is_escalation_request:
                session.escalation_required = True
            
            db.commit()
            
            logger.info(
                f"SIACASA Message recorded - Session: {session_id}, "
                f"Intent: {intent}, Sentiment: {sentiment}, "
                f"Processing: {processing_time_ms}ms"
            )
            
        except SQLAlchemyError as e:
            logger.error(f"Error recording SIACASA message: {e}")
            db.rollback()
            raise
        finally:
            db.close()
    
    def end_session_sync(
        self,
        session_id: UUID,
        resolution_status: str,
        satisfaction_score: Optional[int] = None,
        escalation_required: bool = False
    ) -> None:
        """Versión síncrona para finalizar sesión"""
        
        session_generator = get_database_session()
        db = next(session_generator)
        
        try:
            session = db.query(DBSession).filter(DBSession.id == session_id).first()
            if not session:
                logger.warning(f"Session not found for ending: {session_id}")
                return
            
            session.end_time = datetime.utcnow()
            session.resolution_status = resolution_status
            session.escalation_required = escalation_required
            session.satisfaction_score = satisfaction_score
            
            db.commit()
            
            # Limpiar de memoria
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            
            # Log métricas finales
            duration = (session.end_time - session.start_time).total_seconds()
            logger.info(
                f"SIACASA Session ended - ID: {session_id}, "
                f"Duration: {duration}s, Messages: {session.total_messages}, "
                f"Resolution: {resolution_status}, "
                f"Satisfaction: {satisfaction_score or 'N/A'}"
            )
            
        except SQLAlchemyError as e:
            logger.error(f"Error ending SIACASA session: {e}")
            db.rollback()
            raise
        finally:
            db.close()
    
    def get_or_create_session_for_user(self, user_id: str) -> UUID:
        """Obtiene sesión activa o crea una nueva para el usuario"""
        
        session_generator = get_database_session()
        db = next(session_generator)
        
        try:
            # Buscar sesión activa (sin end_time)
            active_session = db.query(DBSession).filter(
                DBSession.user_id == user_id,
                DBSession.end_time.is_(None)
            ).first()
            
            if active_session:
                logger.info(f"Found active session {active_session.id} for user {user_id}")
                return active_session.id
            
            # Crear nueva sesión
            new_session = DBSession(
                user_id=user_id,
                cliente_type=ClienteType.RECURRENTE.value,
                initial_sentiment=SentimentType.NEUTRAL.value
            )
            
            db.add(new_session)
            db.commit()
            db.refresh(new_session)
            
            logger.info(f"Created new session {new_session.id} for user {user_id}")
            return new_session.id
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting/creating session for user {user_id}: {e}")
            db.rollback()
            raise
        finally:
            db.close()

# Instancia global
metrics_collector = SIACASAMetricsCollector()