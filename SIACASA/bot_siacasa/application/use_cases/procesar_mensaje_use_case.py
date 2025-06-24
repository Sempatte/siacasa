# bot_siacasa/application/use_cases/procesar_mensaje_use_case.py
import uuid
import time
import logging
from typing import Dict, Optional

from bot_siacasa.domain.services.chatbot_service import ChatbotService

logger = logging.getLogger(__name__)


class ProcesarMensajeUseCase:
    """
    Caso de uso optimizado para procesar mensajes del chatbot.
    Versión simplificada y optimizada para máximo rendimiento.
    """

    def __init__(self, chatbot_service: ChatbotService, metrics_collector=None):
        """
        Inicializa el caso de uso.
        
        Args:
            chatbot_service: Servicio del chatbot
            metrics_collector: Collector de métricas (opcional)
        """
        self.chatbot_service = chatbot_service
        self.metrics_collector = metrics_collector

    def execute(self, mensaje_usuario: str, usuario_id: str, info_usuario: Dict = None) -> str:
        """
        Ejecuta el procesamiento de mensaje de forma optimizada.
        
        Args:
            mensaje_usuario: Mensaje del usuario
            usuario_id: ID del usuario
            info_usuario: Información adicional del usuario (opcional)
            
        Returns:
            Respuesta del chatbot
        """
        total_start_time = time.perf_counter()
        
        try:
            # Validación básica de entrada
            if not mensaje_usuario or not mensaje_usuario.strip():
                logger.warning(f"Mensaje vacío recibido de usuario {usuario_id}")
                return "Por favor, escribe un mensaje para poder ayudarte."
            
            if not usuario_id:
                logger.warning("Usuario ID vacío recibido")
                usuario_id = str(uuid.uuid4())  # Generar ID temporal
            
            # Log de inicio
            logger.info(f"🚀 Procesando mensaje de usuario {usuario_id}: '{mensaje_usuario[:50]}{'...' if len(mensaje_usuario) > 50 else ''}'")
            
            # 1. VERIFICAR SI LA CONVERSACIÓN ESTÁ ESCALADA
            if self._is_escalated(usuario_id):
                response = "Tu consulta ha sido escalada a un agente humano. Un agente te atenderá lo antes posible."
                total_time = (time.perf_counter() - total_start_time) * 1000
                logger.info(f"✅ Respuesta escalación en {total_time:.1f}ms")
                return response
            
            # 2. VERIFICAR SI NECESITA ESCALACIÓN INMEDIATA
            if self._should_escalate_immediately(mensaje_usuario, usuario_id):
                response = "He escalado tu consulta a un agente humano. Te atenderán lo antes posible. Mientras tanto, puedes seguir escribiendo."
                total_time = (time.perf_counter() - total_start_time) * 1000
                logger.info(f"✅ Nueva escalación en {total_time:.1f}ms")
                return response
            
            # 3. PROCESAR MENSAJE NORMALMENTE (método principal optimizado)
            # ⭐ CLAVE: Usar el método principal que mantiene contexto Y tiene optimizaciones
            respuesta = self.chatbot_service.procesar_mensaje(
                usuario_id=usuario_id,
                texto_mensaje= mensaje_usuario,
                info_usuario=info_usuario
            )

            # 4. Métricas básicas
            total_time = (time.perf_counter() - total_start_time) * 1000
            logger.info(f"✅ RESPUESTA generada en {total_time:.1f}ms para usuario {usuario_id}")

            # 5. Registrar métricas básicas (opcional)
            self._record_basic_metrics(usuario_id, mensaje_usuario, respuesta, total_time)

            return respuesta

        except Exception as e:
            total_time = (time.perf_counter() - total_start_time) * 1000
            logger.error(f"❌ ERROR procesando mensaje ({total_time:.1f}ms): {e}", exc_info=True)
            return "Lo siento, estoy experimentando problemas técnicos en este momento. ¿Podrías intentarlo de nuevo más tarde?"

    def _is_escalated(self, usuario_id: str) -> bool:
        """Verifica si la conversación ya está escalada"""
        try:
            return self.chatbot_service.esta_escalada(usuario_id)
        except Exception as e:
            logger.debug(f"Error verificando escalación: {e}")
            return False

    def _should_escalate_immediately(self, mensaje: str, usuario_id: str) -> bool:
        """Verifica si debe escalar inmediatamente"""
        try:
            return self.chatbot_service.check_for_escalation(mensaje, usuario_id)
        except Exception as e:
            logger.debug(f"Error verificando escalación inmediata: {e}")
            return False

    def _record_basic_metrics(self, usuario_id: str, mensaje: str, respuesta: str, tiempo_ms: float):
        """Registra métricas básicas si el collector está disponible"""
        try:
            if hasattr(self.metrics_collector, 'record_conversation'):
                # Métricas simplificadas para no afectar rendimiento
                self.metrics_collector.record_conversation(
                    session_id=usuario_id,
                    user_message=mensaje,
                    bot_response=respuesta,
                    processing_time_ms=tiempo_ms,
                    sentiment="neutral",  # Simplificado para velocidad
                    intent="general"     # Simplificado para velocidad
                )
        except Exception as e:
            logger.debug(f"Error registrando métricas básicas: {e}")

    # Métodos de compatibilidad (mantenidos para no romper código existente)
    def _analyze_sentiment_safe(self, mensaje: str):
        """Análisis de sentimiento seguro - SIMPLIFICADO para compatibilidad"""
        try:
            return self.chatbot_service.analizar_sentimiento_mensaje(mensaje)
        except Exception as e:
            logger.debug(f"Error analizando sentimiento: {e}")
            
            class MockSentiment:
                sentimiento = "neutral"
                confianza = 0.5
                emociones = []
                entidades = {}
            return MockSentiment()

    def _get_or_create_session_safe(self, usuario_id: str) -> str:
        """Obtiene o crea sesión de forma segura - SIMPLIFICADO"""
        try:
            return usuario_id  # Para simplicidad, usar el usuario_id como session_id
        except Exception as e:
            logger.debug(f"Error creando sesión: {e}")
            return str(uuid.uuid4())

    def _get_optimized_history(self, usuario_id: str, max_messages: int = 15) -> list:
        """Obtiene historial optimizado con límite"""
        try:
            return self.chatbot_service.obtener_historial_mensajes(usuario_id, max_messages)
        except Exception as e:
            logger.debug(f"Error obteniendo historial: {e}")
            return [{"role": "system", "content": "Eres SIACASA, un asistente bancario virtual."}]