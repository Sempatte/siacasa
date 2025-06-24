import logging
import time
from datetime import datetime
from typing import Dict, Optional, Any
from bot_siacasa.infrastructure.db.neondb_connector import NeonDBConnector

logger = logging.getLogger(__name__)

class MetricsCollector:
    """
    Collector de métricas optimizado para usar tu estructura de BD existente
    """
    
    def __init__(self):
        self.db_connector = NeonDBConnector()
    
    def get_or_create_session_for_user(self, user_id: str) -> str:
        """
        Obtiene o crea una sesión en chat_sessions para el usuario
        """
        try:
            # Buscar sesión activa (sin end_time)
            existing_session = self.db_connector.fetch_one("""
                SELECT id FROM chat_sessions 
                WHERE user_id = %s AND end_time IS NULL 
                ORDER BY start_time DESC 
                LIMIT 1
            """, (user_id,))
            
            if existing_session:
                return str(existing_session['id'])
            
            # Crear nueva sesión
            import uuid
            session_id = str(uuid.uuid4())
            
            self.db_connector.execute("""
                INSERT INTO chat_sessions (
                    id, user_id, start_time, initial_sentiment,
                    total_messages, escalation_required
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                session_id, user_id, datetime.now(), 
                'neutral', 0, False
            ))
            
            logger.debug(f"Nueva sesión creada: {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error obteniendo/creando sesión: {e}")
            return str(uuid.uuid4())  # Fallback
    
    def record_message_sync(self, **kwargs):
        """
        Registra métricas de mensaje en la BD usando OPCIÓN 1 (tabla mensajes)
        """
        try:
            session_id = kwargs.get('session_id')
            processing_time_ms = kwargs.get('processing_time_ms', 0)
            ai_processing_time_ms = kwargs.get('ai_processing_time_ms', 0)
            
            # Obtener el último mensaje para este session/usuario
            last_message = self.db_connector.fetch_one("""
                SELECT m.id, m.conversacion_id
                FROM mensajes m
                JOIN conversaciones c ON m.conversacion_id = c.id
                JOIN chat_sessions cs ON cs.user_id = c.usuario_id
                WHERE cs.id = %s
                ORDER BY m.timestamp DESC
                LIMIT 1
            """, (session_id,))
            
            if last_message:
                # Actualizar el mensaje con métricas
                self.db_connector.execute("""
                    UPDATE mensajes SET
                        processing_time_ms = %s,
                        ai_processing_time_ms = %s,
                        sentiment = %s,
                        sentiment_confidence = %s,
                        intent = %s,
                        intent_confidence = %s,
                        token_count = %s,
                        is_escalation_request = %s,
                        response_tone = %s,
                        metadata = COALESCE(metadata, '{}'::jsonb) || %s::jsonb
                    WHERE id = %s
                """, (
                    processing_time_ms,
                    ai_processing_time_ms,
                    kwargs.get('sentiment', 'neutral'),
                    kwargs.get('sentiment_confidence', 0.5),
                    kwargs.get('intent', 'otro'),
                    kwargs.get('intent_confidence', 0.5),
                    kwargs.get('token_count', 0),
                    kwargs.get('is_escalation_request', False),
                    kwargs.get('response_tone', 'neutral'),
                    json.dumps({
                        'detected_entities': kwargs.get('detected_entities', {}),
                        'timing_breakdown': kwargs.get('timing_breakdown', {})
                    }),
                    last_message['id']
                ))
            
            # Actualizar métricas de la sesión
            self._update_session_metrics(session_id, processing_time_ms)
            
            logger.debug(f"Métricas registradas: {processing_time_ms:.1f}ms")
            
        except Exception as e:
            logger.error(f"Error registrando métricas: {e}")
    
    def record_message_with_timing_breakdown(self, **kwargs):
        """
        Versión extendida que guarda breakdown detallado de tiempos
        """
        try:
            # Usar OPCIÓN 2 (tabla message_metrics) para métricas detalladas
            
            import json
            
            self.db_connector.execute("""
                INSERT INTO message_metrics (
                    session_id, user_message, bot_response,
                    sentiment, sentiment_confidence, intent, intent_confidence,
                    processing_time_ms, ai_processing_time_ms, database_time_ms,
                    token_count, is_escalation_request, detected_entities,
                    response_tone, timing_breakdown
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                kwargs.get('session_id'),
                kwargs.get('user_message', ''),
                kwargs.get('bot_response', ''),
                kwargs.get('sentiment', 'neutral'),
                kwargs.get('sentiment_confidence', 0.5),
                kwargs.get('intent', 'otro'),
                kwargs.get('intent_confidence', 0.5),
                kwargs.get('total_processing_time_ms', 0),
                kwargs.get('ai_processing_time_ms', 0),
                kwargs.get('database_time_ms', 0),
                kwargs.get('token_count', 0),
                kwargs.get('is_escalation_request', False),
                json.dumps(kwargs.get('detected_entities', {})),
                kwargs.get('response_tone', 'neutral'),
                json.dumps(kwargs.get('timing_breakdown', {}))
            ))
            
            # También actualizar tabla principal
            self.record_message_sync(**kwargs)
            
        except Exception as e:
            logger.error(f"Error registrando métricas extendidas: {e}")
            # Fallback a método simple
            self.record_message_sync(**kwargs)
    
    def _update_session_metrics(self, session_id: str, processing_time_ms: float):
        """
        Actualiza métricas agregadas de la sesión
        """
        try:
            # Incrementar contador de mensajes y actualizar tiempo promedio
            self.db_connector.execute("""
                UPDATE chat_sessions SET
                    total_messages = COALESCE(total_messages, 0) + 1,
                    total_processing_time_ms = COALESCE(total_processing_time_ms, 0) + %s,
                    avg_response_time_ms = (
                        COALESCE(total_processing_time_ms, 0) + %s
                    ) / (COALESCE(total_messages, 0) + 1),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (processing_time_ms, processing_time_ms, session_id))
            
        except Exception as e:
            logger.error(f"Error actualizando métricas de sesión: {e}")

# Instancia global
metrics_collector = MetricsCollector()