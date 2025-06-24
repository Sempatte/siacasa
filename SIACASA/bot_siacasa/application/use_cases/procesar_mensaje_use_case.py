import time
import logging
import uuid
from datetime import datetime
from typing import Dict, Optional

from bot_siacasa.metrics.collector import metrics_collector
from bot_siacasa.application.interfaces.ia_provider_interface import IAProviderInterface
from bot_siacasa.metrics.models import SentimentType, IntentType

logger = logging.getLogger(__name__)


class ProcesarMensajeUseCase:
    """
    Caso de uso principal para procesar mensajes del usuario.
    VERSIÓN SIMPLIFICADA: Usa directamente el método procesar_mensaje del ChatbotService.
    """

    def __init__(self, chatbot_service, ai_provider: IAProviderInterface):
        """
        Inicializa el caso de uso.

        Args:
            chatbot_service: Servicio de chatbot
            ai_provider: Proveedor de IA para generar respuestas
        """
        self.chatbot_service = chatbot_service
        self.ai_provider = ai_provider
        self.metrics_collector = metrics_collector

        # Asegurar que el chatbot_service tenga el ai_provider
        if hasattr(chatbot_service, 'ai_provider') and chatbot_service.ai_provider is None:
            chatbot_service.ai_provider = ai_provider

    def execute(self, mensaje_usuario: str, usuario_id: Optional[str] = None, info_usuario: Optional[Dict] = None) -> str:
        """
        Procesa un mensaje del usuario y genera una respuesta.
        SIMPLIFICADO: Delega toda la lógica al ChatbotService.

        Args:
            mensaje_usuario: Texto del mensaje del usuario
            usuario_id: ID del usuario (opcional, se generará uno si no se proporciona)
            info_usuario: Información adicional del usuario (opcional)

        Returns:
            Texto de la respuesta generada
        """
        total_start_time = time.perf_counter()

        try:
            # 1. Validación básica
            if not mensaje_usuario or not mensaje_usuario.strip():
                return "Por favor, escribe un mensaje para poder ayudarte."

            # 2. Generar ID de usuario si no se proporciona
            if not usuario_id:
                usuario_id = str(uuid.uuid4())

            logger.info(
                f"🚀 PROCESANDO mensaje para usuario {usuario_id}: {mensaje_usuario[:50]}...")

            # 3. Actualizar información del usuario si se proporciona
            if info_usuario:
                try:
                    self.chatbot_service.actualizar_datos_usuario(
                        usuario_id, info_usuario)
                    logger.debug(
                        f"✅ Datos de usuario actualizados para {usuario_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Error actualizando datos usuario: {e}")

            # 4. ⭐ CLAVE: Usar el método principal que mantiene contexto
            respuesta = self.chatbot_service.procesar_mensaje(
                usuario_id=usuario_id,
                texto=mensaje_usuario,
                info_usuario=info_usuario
            )

            # 5. Métricas básicas
            total_time = (time.perf_counter() - total_start_time) * 1000
            logger.info(
                f"✅ RESPUESTA generada en {total_time:.1f}ms para usuario {usuario_id}")

            # 6. Registrar métricas básicas si el collector está disponible
            try:
                if hasattr(self.metrics_collector, 'record_conversation'):
                    self.metrics_collector.record_conversation(
                        session_id=usuario_id,
                        user_message=mensaje_usuario,
                        bot_response=respuesta,
                        processing_time_ms=total_time,
                        sentiment=SentimentType.NEUTRAL,  # Simplificado
                        intent=IntentType.INFORMATION    # Simplificado
                    )
            except Exception as e:
                logger.debug(f"Error registrando métricas: {e}")

            return respuesta

        except Exception as e:
            total_time = (time.perf_counter() - total_start_time) * 1000
            logger.error(
                f"❌ ERROR procesando mensaje ({total_time:.1f}ms): {e}", exc_info=True)
            return "Lo siento, estoy experimentando problemas técnicos en este momento. ¿Podrías intentarlo de nuevo más tarde?"

    # Métodos auxiliares simplificados (mantenidos por compatibilidad)
    def _analyze_sentiment_safe(self, mensaje: str):
        """Analiza sentimiento de forma segura - SIMPLIFICADO"""
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
            # Para simplicidad, usar el usuario_id como session_id
            return usuario_id
        except Exception as e:
            logger.debug(f"Error creando sesión: {e}")
            return str(uuid.uuid4())

    def _check_escalation_status(self, usuario_id: str) -> bool:
        """Verifica estado de escalación - SIMPLIFICADO"""
        try:
            return self.chatbot_service.esta_escalada(usuario_id)
        except Exception as e:
            logger.debug(f"Error verificando escalación: {e}")
            return False

    def _should_escalate(self, mensaje: str, usuario_id: str) -> bool:
        """Determina si debe escalar a humano"""
        try:
            if hasattr(self.chatbot_service, 'check_for_escalation'):
                result = self.chatbot_service.check_for_escalation(
                    mensaje, usuario_id)
                logger.info(f"Escalation check result: {result}")
                return result
        except Exception as e:
            logger.error(f"Error verificando escalación: {e}")
        return False

    def _analyze_sentiment_safe(self, mensaje: str):
        """Analiza sentimiento de forma segura"""
        try:
            return self.chatbot_service.analizar_sentimiento_mensaje(mensaje)
        except Exception as e:
            logger.error(f"Error analizando sentimiento: {e}")
            # Retornar objeto mock con valores por defecto

            class MockSentiment:
                sentimiento = "neutral"
                confianza = 0.5
                emociones = []
                entidades = {}
            return MockSentiment()

    def _get_optimized_history(self, usuario_id: str, max_messages: int = 20) -> list:
        """Obtiene historial optimizado con límite"""
        try:
            # CORRECCIÓN: Implementar límite real en la consulta
            if hasattr(self.chatbot_service, 'obtener_historial_limitado'):
                return self.chatbot_service.obtener_historial_limitado(usuario_id, max_messages)
            else:
                # Fallback: obtener todo y limitar en memoria (no óptimo)
                mensajes = self.chatbot_service.obtener_historial_mensajes(
                    usuario_id)
                if len(mensajes) > max_messages:
                    # Mantener mensaje de sistema + últimos N mensajes
                    system_messages = [
                        m for m in mensajes if m.get('role') == 'system']
                    other_messages = [
                        m for m in mensajes if m.get('role') != 'system']
                    return system_messages + other_messages[-(max_messages-len(system_messages)):]
                return mensajes
        except Exception as e:
            logger.error(f"Error obteniendo historial: {e}")
            # Retornar historial mínimo
            return [{"role": "system", "content": "Eres un asistente bancario virtual helpful."}]

    def _classify_intent_safe(self, mensaje: str, datos_sentimiento) -> str:
        """Clasifica la intención del mensaje de forma segura"""
        try:
            mensaje_lower = mensaje.lower()

            # Patrones mejorados con más palabras clave
            intent_patterns = {
                IntentType.CONSULTA_SALDO.value: ['saldo', 'cuenta', 'dinero', 'plata', 'balance', 'disponible'],
                IntentType.TRANSFERENCIA.value: ['transferir', 'enviar', 'transferencia', 'envío', 'mandar'],
                IntentType.PRESTAMO_PERSONAL.value: ['prestamo', 'credito', 'prestar', 'financiamiento'],
                IntentType.PRESTAMO_AGRICOLA.value: ['agricola', 'campo', 'cosecha', 'rural', 'agricultura'],
                IntentType.RECLAMO.value: ['reclamo', 'queja', 'problema', 'error', 'inconveniente'],
                IntentType.SALUDO.value: ['hola', 'buenos', 'buenas', 'saludos', 'hey', 'hi'],
                IntentType.DESPEDIDA.value: [
                    'adios', 'gracias', 'hasta luego', 'chau', 'bye']
            }

            for intent, keywords in intent_patterns.items():
                if any(keyword in mensaje_lower for keyword in keywords):
                    return intent

            return IntentType.OTRO.value

        except Exception as e:
            logger.error(f"Error clasificando intent: {e}")
            return IntentType.OTRO.value

    def _prepare_instructions(self, mensajes: list, datos_sentimiento, mensaje_count_before: int) -> str:
        """Prepara instrucciones optimizadas"""
        try:
            instrucciones = f"""
CONTEXTO ACTUAL:
Esta conversación tiene {len(mensajes)} mensajes anteriores que DEBES usar para mantener el contexto.

INFORMACIÓN SOBRE EL SENTIMIENTO:
- Sentimiento detectado: {datos_sentimiento.sentimiento}
- Nivel de confianza: {datos_sentimiento.confianza}
- Emociones detectadas: {', '.join(getattr(datos_sentimiento, 'emociones', []))}

INSTRUCCIONES IMPORTANTES:
1. USA la información de los mensajes anteriores para dar contexto a tu respuesta.
2. NO digas que no puedes recordar la conversación.
3. Si el usuario hace referencia a algo mencionado previamente, RESPONDE basado en esa información.
4. Adapta tu tono al estado emocional del cliente.
5. Si el usuario pide hablar con un humano o muestra frustración, sugiere: "Si prefieres, puedo transferir esta conversación a un agente humano."
"""

            if mensaje_count_before <= 1:
                instrucciones += """
Esta es la primera interacción. Da la bienvenida como asistente virtual bancario.
"""

            return instrucciones

        except Exception as e:
            logger.error(f"Error preparando instrucciones: {e}")
            return "Eres un asistente bancario virtual helpful."

    def _handle_escalated_conversation(self, usuario_id: str, mensaje: str, session_id: str, start_time: float) -> str:
        """Maneja conversaciones ya escaladas"""
        logger.info(
            f"Conversación ya escalada para usuario {usuario_id}, notificando al agente")

        self._notificar_agente_nuevo_mensaje(usuario_id, mensaje)

        respuesta = "Tu mensaje ha sido recibido. Un agente humano te responderá en breve. Por favor, ten paciencia."

        processing_time_ms = (time.perf_counter() - start_time) * 1000
        self._record_escalation_metrics(
            session_id, mensaje, respuesta, processing_time_ms)

        return respuesta

    def _handle_new_escalation(self, usuario_id: str, mensaje: str, session_id: str, start_time: float) -> str:
        """Maneja nueva escalación"""
        respuesta = "Tu consulta ha sido escalada a un agente humano. Un agente te atenderá lo antes posible. Mientras tanto, puedes seguir escribiendo y tu mensaje será visible para el agente cuando se conecte."

        processing_time_ms = (time.perf_counter() - start_time) * 1000
        self._record_escalation_metrics(
            session_id, mensaje, respuesta, processing_time_ms, True)

        return respuesta

    def _estimate_token_count(self, user_message: str, bot_response: str) -> int:
        """Estima el número de tokens usando conteo de palabras"""
        try:
            user_words = len(user_message.split())
            bot_words = len(bot_response.split())
            return int((user_words + bot_words) * 1.3)
        except Exception:
            return 0

    def _record_enhanced_metrics(
        self,
        session_id: str,
        user_message: str,
        bot_response: str,
        sentiment: str,
        sentiment_confidence: float,
        intent: str,
        ai_processing_time_ms: float,
        total_processing_time_ms: float,
        token_count: int,
        detected_entities=None,
        response_time_breakdown=None,
        is_escalation_request: bool = False
    ):
        """Registra métricas mejoradas con breakdown de tiempos"""
        try:
            sentiment_mapped = sentiment if sentiment in [
                s.value for s in SentimentType] else SentimentType.NEUTRAL.value

            # Datos base
            metrics_data = {
                'session_id': session_id,
                'user_message': user_message,
                'bot_response': bot_response,
                'sentiment': sentiment_mapped,
                'sentiment_confidence': sentiment_confidence,
                'intent': intent,
                'intent_confidence': 0.8,
                'processing_time_ms': total_processing_time_ms,
                'token_count': token_count,
                'is_escalation_request': is_escalation_request,
                'detected_entities': detected_entities or {},
                'response_tone': "amigable"
            }

            # Agregar métricas extendidas si están disponibles
            if hasattr(self.metrics_collector, 'record_message_with_breakdown'):
                metrics_data.update({
                    'ai_processing_time_ms': ai_processing_time_ms,
                    'response_time_breakdown': response_time_breakdown or {}
                })
                self.metrics_collector.record_message_with_breakdown(
                    **metrics_data)
            else:
                # Fallback a método estándar
                self.metrics_collector.record_message_sync(**metrics_data)

        except Exception as e:
            logger.error(f"Error recording enhanced metrics: {e}")

    def _record_escalation_metrics(
        self,
        session_id: str,
        user_message: str,
        bot_response: str,
        processing_time_ms: float,
        is_new_escalation: bool = False
    ):
        """Registra métricas para escalaciones"""
        try:
            self.metrics_collector.record_message_sync(
                session_id=session_id,
                user_message=user_message,
                bot_response=bot_response,
                sentiment=SentimentType.NEUTRAL.value,
                sentiment_confidence=0.5,
                intent=IntentType.RECLAMO.value if is_new_escalation else IntentType.OTRO.value,
                intent_confidence=0.9 if is_new_escalation else 0.7,
                processing_time_ms=processing_time_ms,
                token_count=self._estimate_token_count(
                    user_message, bot_response),
                is_escalation_request=True,
                response_tone="comprensivo"
            )
        except Exception as e:
            logger.error(f"Error recording escalation metrics: {e}")

    def _record_error_metrics(
        self,
        session_id: str,
        user_message: str,
        processing_time_ms: float
    ):
        """Registra métricas para errores"""
        try:
            self.metrics_collector.record_message_sync(
                session_id=session_id,
                user_message=user_message,
                bot_response="Error interno del sistema",
                sentiment=SentimentType.NEGATIVO.value,
                sentiment_confidence=0.9,
                intent=IntentType.OTRO.value,
                intent_confidence=0.3,
                processing_time_ms=processing_time_ms,
                token_count=len(user_message.split()) * 2,
                is_escalation_request=False,
                response_tone="disculpa"
            )
        except Exception as e:
            logger.error(f"Error recording error metrics: {e}")

    def _notificar_agente_nuevo_mensaje(self, usuario_id: str, mensaje: str) -> None:
        """
        Notifica a los agentes asignados que hay un nuevo mensaje del usuario.
        Versión corregida con mejor manejo de errores.
        """
        try:
            if not hasattr(self.chatbot_service, 'support_repository'):
                logger.debug(
                    "No hay repositorio de soporte disponible para la notificación")
                return

            support_repo = self.chatbot_service.support_repository

            try:
                # Importar dinámicamente para evitar dependencias circulares
                from bot_siacasa.infrastructure.websocket.socketio_server import get_socketio_server

                socketio_server = get_socketio_server()
                if not socketio_server:
                    logger.debug("No hay servidor SocketIO disponible")
                    return

                # Obtener tickets activos del usuario
                tickets = support_repo.obtener_tickets_por_usuario(usuario_id)
                active_tickets = [t for t in tickets if t.estado.value in [
                    'pending', 'assigned', 'active']]

                if not active_tickets:
                    logger.debug(
                        f"No hay tickets activos para usuario {usuario_id}")
                    return

                ticket = active_tickets[0]

                message_data = {
                    'type': 'chat_message',
                    'ticket_id': str(ticket.id),
                    'content': mensaje,
                    'sender_id': usuario_id,
                    'sender_name': getattr(ticket.usuario, 'nombre', 'Usuario'),
                    'sender_type': 'user',
                    'is_internal': False,
                    'timestamp': datetime.now().isoformat()
                }

                if hasattr(socketio_server, 'socketio'):
                    ticket_room = f'ticket_{ticket.id}'
                    socketio_server.socketio.emit(
                        'chat_message', message_data, room=ticket_room)

                    if ticket.agente_id and hasattr(socketio_server, 'agent_connections'):
                        if ticket.agente_id in socketio_server.agent_connections:
                            agent_sid = socketio_server.agent_connections[ticket.agente_id]
                            socketio_server.socketio.emit(
                                'new_user_message', message_data, room=agent_sid)

                logger.info(f"Notificación enviada para ticket {ticket.id}")

            except ImportError:
                logger.debug("Módulos WebSocket no disponibles")
            except Exception as e:
                logger.warning(f"Error en notificación WebSocket: {e}")

        except Exception as e:
            logger.error(f"Error notificando agentes: {e}")
