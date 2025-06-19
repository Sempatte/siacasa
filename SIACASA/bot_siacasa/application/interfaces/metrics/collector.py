import logging
from datetime import datetime
from typing import Optional
from uuid import UUID
import asyncio

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from metrics.database import get_db, DBSession, DBMessage
from metrics.models import (
    SentimentType, IntentType, ResolutionStatus,
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
        cliente_tipo: Optional[str] = None
    ) -> UUID:
        """Iniciar nueva sesión de usuario"""
        
        db = next(get_db())
        try:
            session = DBSession(
                user_id=user_id,
                cliente_tipo=cliente_tipo or "regular",
                initial_sentiment=SentimentType.NEUTRAL
            )
            
            db.add(session)
            db.commit()
            db.refresh(session)
            
            # Mantener en memoria para acceso rápido
            self.active_sessions[session.id] = {
                'start_time': session.start_time,
                'sentiment_journey': [SentimentType.NEUTRAL],
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
    
    async def record_message(
        self,
        session_id: UUID,
        metric: MessageMetric
    ) -> None:
        """Registrar mensaje y actualizar métricas de sesión"""
        
        db = next(get_db())
        try:
            # Verificar sesión existe
            session = db.query(DBSession).filter(DBSession.id == session_id).first()
            if not session:
                raise ValueError(f"SIACASA Session not found: {session_id}")
            
            # Crear registro de mensaje
            message = DBMessage(
                session_id=session_id,
                user_message=metric.user_message,
                bot_response=metric.bot_response,
                sentiment=metric.sentiment,
                sentiment_confidence=metric.sentiment_confidence,
                intent=metric.intent,
                intent_confidence=metric.intent_confidence,
                processing_time_ms=metric.processing_time_ms,
                token_count=metric.token_count,
                is_escalation_request=metric.is_escalation_request,
                user_satisfaction=metric.user_satisfaction
            )
            
            db.add(message)
            
            # Actualizar métricas de sesión
            session.total_messages += 1
            session.total_processing_time_ms += metric.processing_time_ms
            session.total_tokens_used += metric.token_count
            
            # Actualizar journey de sentimientos
            if session_id in self.active_sessions:
                journey = self.active_sessions[session_id]['sentiment_journey']
                if journey[-1] != metric.sentiment:
                    journey.append(metric.sentiment)
                
                # Detectar mejora emocional
                if (len(journey) >= 2 and 
                    journey[0] == SentimentType.NEGATIVO and 
                    metric.sentiment in [SentimentType.NEUTRAL, SentimentType.POSITIVO]):
                    session.emotion_improvement = True
                
                # Contar queries resueltas (si no es escalación)
                if not metric.is_escalation_request:
                    session.queries_resolved += 1
                    self.active_sessions[session_id]['queries_resolved'] += 1
            
            # Actualizar sentimiento final
            session.final_sentiment = metric.sentiment
            
            # Si es primer mensaje, establecer sentimiento inicial
            if session.total_messages == 1:
                session.initial_sentiment = metric.sentiment
            
            db.commit()
            
            logger.info(
                f"SIACASA Message recorded - Session: {session_id}, "
                f"Intent: {metric.intent}, Sentiment: {metric.sentiment}, "
                f"Processing: {metric.processing_time_ms}ms"
            )
            
        except SQLAlchemyError as e:
            logger.error(f"Error recording SIACASA message: {e}")
            db.rollback()
            raise
        finally:
            db.close()
    
    async def end_session(
        self,
        session_id: UUID,
        resolution_status: ResolutionStatus,
        satisfaction_score: Optional[int] = None,
        escalation_required: bool = False
    ) -> SessionMetric:
        """Finalizar sesión y calcular métricas finales"""
        
        db = next(get_db())
        try:
            session = db.query(DBSession).filter(DBSession.id == session_id).first()
            if not session:
                raise ValueError(f"SIACASA Session not found: {session_id}")
            
            session.end_time = datetime.utcnow()
            session.resolution_status = resolution_status
            session.escalation_required = escalation_required
            session.satisfaction_score = satisfaction_score
            
            # Calcular métricas finales
            if session_id in self.active_sessions:
                session_data = self.active_sessions[session_id]
                
                # Almacenar journey de sentimientos como JSON
                journey_str = ",".join([s.value for s in session_data['sentiment_journey']])
                # Esto requeriría un campo JSON en la DB
                
                del self.active_sessions[session_id]
            
            db.commit()
            
            # Crear métrica de sesión para retornar
            duration = (session.end_time - session.start_time).total_seconds()
            
            session_metric = SessionMetric(
                id=session.id,
                user_id=session.user_id,
                cliente_tipo=session.cliente_tipo,
                start_time=session.start_time,
                end_time=session.end_time,
                initial_sentiment=session.initial_sentiment,
                final_sentiment=session.final_sentiment,
                resolution_status=session.resolution_status,
                total_messages=session.total_messages,
                escalation_required=session.escalation_required,
                satisfaction_score=session.satisfaction_score,
                emotion_improvement=session.emotion_improvement,
                queries_resolved=session.queries_resolved,
                total_processing_time_ms=session.total_processing_time_ms,
                total_tokens_used=session.total_tokens_used
            )
            
            logger.info(
                f"SIACASA Session ended - ID: {session_id}, "
                f"Duration: {duration}s, Messages: {session.total_messages}, "
                f"Resolution: {resolution_status}, "
                f"Emotion Improved: {session.emotion_improvement}, "
                f"Satisfaction: {satisfaction_score or 'N/A'}"
            )
            
            return session_metric
            
        except SQLAlchemyError as e:
            logger.error(f"Error ending SIACASA session: {e}")
            db.rollback()
            raise
        finally:
            db.close()

# Instancia global
siacasa_metrics = SIACASAMetricsCollector()