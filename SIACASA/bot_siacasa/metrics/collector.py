import logging
import time
import json
from datetime import datetime
from typing import Dict, Optional, Any
from bot_siacasa.infrastructure.db.neondb_connector import NeonDBConnector

logger = logging.getLogger(__name__)

class MetricsCollector:
    """
    Collector de métricas CORREGIDO
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
        ✅ VERSIÓN CORREGIDA - Registra métricas en la BD
        """
        try:
            session_id = kwargs.get('session_id')
            processing_time_ms = kwargs.get('processing_time_ms', 0)
            ai_processing_time_ms = kwargs.get('ai_processing_time_ms', 0)
            user_message = kwargs.get('user_message', '')
            
            # 🔧 MÉTODO CORREGIDO 1: Buscar por user_id directamente
            # Obtener user_id de la sesión
            session_info = self.db_connector.fetch_one("""
                SELECT user_id FROM chat_sessions WHERE id = %s
            """, (session_id,))
            
            if not session_info:
                logger.warning(f"No se encontró sesión {session_id}")
                return
                
            user_id = session_info['user_id']
            
            # Buscar el último mensaje de este usuario
            last_message = self.db_connector.fetch_one("""
                SELECT m.id, m.conversacion_id
                FROM mensajes m
                JOIN conversaciones c ON m.conversacion_id = c.id
                WHERE c.usuario_id = %s
                ORDER BY m.timestamp DESC
                LIMIT 1
            """, (user_id,))
            
            if last_message:
                # ✅ ACTUALIZAR el mensaje con métricas
                rows_updated = self.db_connector.execute("""
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
                
                logger.info(f"✅ Métricas guardadas: {processing_time_ms:.1f}ms (mensaje {last_message['id']}, filas: {rows_updated})")
            else:
                logger.warning(f"❌ No se encontró mensaje para usuario {user_id}")
            
            # ✅ ACTUALIZAR métricas de la sesión
            self._update_session_metrics(session_id, processing_time_ms)
            
        except Exception as e:
            logger.error(f"❌ Error registrando métricas: {e}", exc_info=True)
    
    def record_message_sync_alternative(self, **kwargs):
        """
        🔧 MÉTODO ALTERNATIVO: Guardar métricas por conversacion_id
        Usa este si el método principal falla
        """
        try:
            session_id = kwargs.get('session_id')
            processing_time_ms = kwargs.get('processing_time_ms', 0)
            
            # Método alternativo: usar conversacion_id si está disponible
            conversacion_id = kwargs.get('conversacion_id')  # Pasar esto desde el use case
            
            if conversacion_id:
                # Buscar último mensaje de esta conversación
                last_message = self.db_connector.fetch_one("""
                    SELECT id FROM mensajes 
                    WHERE conversacion_id = %s 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """, (conversacion_id,))
                
                if last_message:
                    self.db_connector.execute("""
                        UPDATE mensajes SET
                            processing_time_ms = %s,
                            sentiment = %s
                        WHERE id = %s
                    """, (
                        processing_time_ms,
                        kwargs.get('sentiment', 'neutral'),
                        last_message['id']
                    ))
                    
                    logger.info(f"✅ Métricas alternativas guardadas: {processing_time_ms:.1f}ms")
                    
        except Exception as e:
            logger.error(f"❌ Error en método alternativo: {e}")
    
    def _update_session_metrics(self, session_id: str, processing_time_ms: float):
        """
        ✅ CORREGIDO: Actualiza métricas agregadas de la sesión
        """
        try:
            rows_updated = self.db_connector.execute("""
                UPDATE chat_sessions SET
                    total_messages = COALESCE(total_messages, 0) + 1,
                    total_processing_time_ms = COALESCE(total_processing_time_ms, 0) + %s,
                    avg_response_time_ms = (
                        COALESCE(total_processing_time_ms, 0) + %s
                    ) / (COALESCE(total_messages, 0) + 1),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (processing_time_ms, processing_time_ms, session_id))
            
            if rows_updated > 0:
                logger.debug(f"✅ Sesión actualizada: {session_id}")
            else:
                logger.warning(f"❌ No se actualizó sesión: {session_id}")
                
        except Exception as e:
            logger.error(f"❌ Error actualizando métricas de sesión: {e}")

    # Mantener los otros métodos igual...
    def record_message_with_timing_breakdown(self, **kwargs):
        """Versión extendida - mantener igual"""
        try:
            # Primero intentar método principal
            self.record_message_sync(**kwargs)
            
            # Si hay tabla message_metrics, también guardar ahí
            # (código existente)
            
        except Exception as e:
            logger.error(f"Error registrando métricas extendidas: {e}")

# Instancia global
metrics_collector = MetricsCollector()

# 🧪 SCRIPT DE PRUEBA PARA VERIFICAR QUE FUNCIONA
def test_metrics_funcionan():
    """
    Script para probar si las métricas se guardan correctamente
    """
    try:
        print("🧪 PROBANDO MÉTRICAS...")
        
        # Simular datos de prueba
        test_user_id = "test_user_123"
        
        # 1. Crear sesión
        session_id = metrics_collector.get_or_create_session_for_user(test_user_id)
        print(f"✅ Sesión creada/obtenida: {session_id}")
        
        # 2. Simular mensaje (esto normalmente lo hace el chatbot)
        from bot_siacasa.infrastructure.db.neondb_connector import NeonDBConnector
        db = NeonDBConnector()
        
        # Crear conversación si no existe
        import uuid
        conv_id = str(uuid.uuid4())
        
        db.execute("""
            INSERT INTO conversaciones (id, usuario_id, fecha_inicio)
            VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (conv_id, test_user_id, datetime.now()))
        
        # Crear mensaje de prueba
        mensaje_id = str(uuid.uuid4())
        db.execute("""
            INSERT INTO mensajes (id, conversacion_id, role, content, timestamp)
            VALUES (%s, %s, %s, %s, %s)
        """, (mensaje_id, conv_id, 'user', 'Mensaje de prueba', datetime.now()))
        
        print(f"✅ Mensaje de prueba creado: {mensaje_id}")
        
        # 3. Registrar métricas
        metrics_collector.record_message_sync(
            session_id=session_id,
            user_message="Mensaje de prueba",
            bot_response="Respuesta de prueba",
            sentiment='neutral',
            sentiment_confidence=0.8,
            intent='test',
            processing_time_ms=123.45,
            token_count=10
        )
        
        print("✅ Métricas registradas")
        
        # 4. Verificar que se guardaron
        result = db.fetch_one("""
            SELECT processing_time_ms, sentiment 
            FROM mensajes 
            WHERE id = %s
        """, (mensaje_id,))
        
        if result and result['processing_time_ms'] == 123.45:
            print("🎉 ¡ÉXITO! Las métricas se guardaron correctamente")
            print(f"   Tiempo: {result['processing_time_ms']}ms")
            print(f"   Sentimiento: {result['sentiment']}")
        else:
            print("❌ Las métricas NO se guardaron")
            print(f"   Resultado: {result}")
        
        # 5. Verificar sesión
        session_result = db.fetch_one("""
            SELECT total_messages, avg_response_time_ms 
            FROM chat_sessions 
            WHERE id = %s
        """, (session_id,))
        
        print(f"📊 Métricas de sesión: {session_result}")
        
    except Exception as e:
        print(f"❌ Error en prueba: {e}")

if __name__ == "__main__":
    test_metrics_funcionan()