import time
import logging
import uuid
from typing import Dict, Optional

from bot_siacasa.metrics.collector import metrics_collector
from bot_siacasa.application.interfaces.ia_provider_interface import IAProviderInterface
from bot_siacasa.metrics.models import SentimentType, IntentType

logger = logging.getLogger(__name__)

class ProcesarMensajeUseCase:
    """
    Caso de uso principal para procesar mensajes del usuario con métricas integradas.
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
        
        if hasattr(chatbot_service, 'ai_provider') and chatbot_service.ai_provider is None:
            chatbot_service.ai_provider = ai_provider
    
    def execute(self, mensaje_usuario: str, usuario_id: Optional[str] = None, info_usuario: Optional[Dict] = None) -> str:
        """
        Procesa un mensaje del usuario y genera una respuesta.
        
        Args:
            mensaje_usuario: Texto del mensaje del usuario
            usuario_id: ID del usuario (opcional, se generará uno si no se proporciona)
            info_usuario: Información adicional del usuario (opcional)
            
        Returns:
            Texto de la respuesta generada
        """
        start_time = time.time()
        session_id = None
        
        try:
            # Si no se proporciona ID de usuario, generar uno nuevo
            if not usuario_id:
                usuario_id = str(uuid.uuid4())
            
            # Obtener o crear sesión para métricas
            session_id = self.metrics_collector.get_or_create_session_for_user(usuario_id)
            
            # Mejorar el logging para depuración
            logger.info(f"Procesando mensaje para usuario {usuario_id}, sesión {session_id}: {mensaje_usuario}")
            
            # Actualizar información del usuario si se proporciona
            if info_usuario:
                self.chatbot_service.actualizar_datos_usuario(usuario_id, info_usuario)
            
            # Obtener la conversación ANTES de agregar mensajes
            conversacion = self.chatbot_service.obtener_o_crear_conversacion(usuario_id)
            mensaje_count_before = len(conversacion.mensajes) if conversacion else 0
            
            # Verificar si la conversación está escalada a un humano
            conversacion_escalada = False
            if hasattr(self.chatbot_service, 'esta_escalada'):
                conversacion_escalada = self.chatbot_service.esta_escalada(usuario_id)
            
            # CORREGIDO: Siempre guardar el mensaje del usuario, independientemente de si está escalado o no
            self.chatbot_service.agregar_mensaje_usuario(usuario_id, mensaje_usuario)
            
            # Si la conversación ya está escalada, notificar al agente y devolver mensaje de espera
            if conversacion_escalada:
                logger.info(f"Conversación ya escalada para usuario {usuario_id}, notificando al agente")
                
                # AÑADIDO: Intentar notificar al agente a través del WebSocket
                self._notificar_agente_nuevo_mensaje(usuario_id, mensaje_usuario)
                
                respuesta = "Tu mensaje ha sido recibido. Un agente humano te responderá en breve. Por favor, ten paciencia."
                
                # Registrar métricas para escalación
                processing_time_ms = (time.time() - start_time) * 1000
                self._record_escalation_metrics(
                    session_id, mensaje_usuario, respuesta, processing_time_ms
                )
                
                return respuesta
            
            # Verificar si debe escalar a un humano
            escalation_result = False
            if hasattr(self.chatbot_service, 'check_for_escalation'):
                try:
                    escalation_result = self.chatbot_service.check_for_escalation(mensaje_usuario, usuario_id)
                    logger.info(f"Escalation check result: {escalation_result}")
                except Exception as e:
                    logger.error(f"Error al verificar escalación: {e}", exc_info=True)
                    escalation_result = False
                
            if escalation_result:
                respuesta = "Tu consulta ha sido escalada a un agente humano. Un agente te atenderá lo antes posible. Mientras tanto, puedes seguir escribiendo y tu mensaje será visible para el agente cuando se conecte."
                
                # Registrar métricas para nueva escalación
                processing_time_ms = (time.time() - start_time) * 1000
                self._record_escalation_metrics(
                    session_id, mensaje_usuario, respuesta, processing_time_ms, True
                )
                
                return respuesta
            
            # Analizar el sentimiento del mensaje
            datos_sentimiento = self.chatbot_service.analizar_sentimiento_mensaje(mensaje_usuario)
            
            # Obtener el historial COMPLETO de mensajes
            mensajes = self.chatbot_service.obtener_historial_mensajes(usuario_id)
            logger.info(f"Historial obtenido con {len(mensajes)} mensajes")
            
            # Log de los primeros mensajes para verificar formato
            for i, msg in enumerate(mensajes[:3]):  # Solo mostrar los primeros 3 para evitar logs gigantes
                logger.info(f"Mensaje #{i}: role={msg['role']}, content={msg['content'][:50]}...")
            
            # Clasificar intent usando análisis GPT-4o
            intent = self._classify_intent(mensaje_usuario, datos_sentimiento)
            
            # Modificar las instrucciones adicionales para ser muy explícito
            # sobre el uso del historial
            instrucciones_adicionales = f"""
            CONTEXTO ACTUAL:
            Esta conversación tiene {len(mensajes)} mensajes anteriores que DEBES usar para mantener el contexto.
            
            INFORMACIÓN SOBRE EL SENTIMIENTO:
            - Sentimiento detectado: {datos_sentimiento.sentimiento}
            - Nivel de confianza: {datos_sentimiento.confianza}
            - Emociones detectadas: {', '.join(datos_sentimiento.emociones)}
            
            INSTRUCCIONES IMPORTANTES:
            1. DEBES usar la información de los mensajes anteriores para dar contexto a tu respuesta.
            2. NO digas que no puedes recordar la conversación o que tienes limitaciones de memoria.
            3. Si el usuario hace referencia a algo mencionado previamente, DEBES responder basado
            en esa información previa.
            4. Adapta tu tono al estado emocional del cliente.
            5. Usa un lenguaje natural y conversacional.
            6. Si el usuario pide hablar con un humano o un agente, o muestra frustración con tus respuestas,
            sugiere que puedes escalarlo a un agente humano. Por ejemplo: "Si prefieres, puedo transferir
            esta conversación a un agente humano que podrá ayudarte con tu consulta."
            """
            
            # Si es el primer mensaje del usuario, modificar instrucciones
            if mensaje_count_before <= 1:  # Solo hay mensaje de sistema
                logger.info("Primera interacción con este usuario, usando saludo inicial")
                # Para el primer mensaje, dar instrucciones de bienvenida
                instrucciones_adicionales += """
                Esta es la primera interacción con este usuario. Da la bienvenida y preséntate
                como asistente virtual bancario, sin asumir información previa.
                """
            
            # Generar respuesta con el modelo de IA
            respuesta = self.ai_provider.generar_respuesta(mensajes, instrucciones_adicionales)
            
            # Agregar la respuesta del asistente a la conversación
            self.chatbot_service.agregar_mensaje_asistente(usuario_id, respuesta)
            
            # Calcular métricas finales
            processing_time_ms = (time.time() - start_time) * 1000
            token_count = self._estimate_token_count(mensaje_usuario, respuesta)
            
            # Registrar métricas del mensaje
            self._record_message_metrics(
                session_id=session_id,
                user_message=mensaje_usuario,
                bot_response=respuesta,
                sentiment=datos_sentimiento.sentimiento,
                sentiment_confidence=datos_sentimiento.confianza,
                intent=intent,
                processing_time_ms=processing_time_ms,
                token_count=token_count,
                detected_entities=getattr(datos_sentimiento, 'entidades', None)
            )
            
            # Registrar la respuesta
            logger.info(f"Respuesta enviada a {usuario_id}: {respuesta[:100]}...")
            
            return respuesta
            
        except Exception as e:
            logger.error(f"Error al procesar mensaje: {e}", exc_info=True)
            
            # Registrar error en métricas si tenemos session_id
            if session_id:
                processing_time_ms = (time.time() - start_time) * 1000
                self._record_error_metrics(session_id, mensaje_usuario, processing_time_ms)
            
            return "Lo siento, ocurrió un error al procesar tu mensaje. Por favor, inténtalo de nuevo."
    
    def _classify_intent(self, mensaje: str, datos_sentimiento) -> str:
        """Clasifica la intención del mensaje"""
        try:
            # Mapeo simple basado en palabras clave
            mensaje_lower = mensaje.lower()
            
            if any(word in mensaje_lower for word in ['saldo', 'cuenta', 'dinero', 'plata']):
                return IntentType.CONSULTA_SALDO.value
            elif any(word in mensaje_lower for word in ['transferir', 'enviar', 'transferencia']):
                return IntentType.TRANSFERENCIA.value
            elif any(word in mensaje_lower for word in ['prestamo', 'credito', 'prestar']):
                return IntentType.PRESTAMO_PERSONAL.value
            elif any(word in mensaje_lower for word in ['agricola', 'campo', 'cosecha']):
                return IntentType.PRESTAMO_AGRICOLA.value
            elif any(word in mensaje_lower for word in ['reclamo', 'queja', 'problema']):
                return IntentType.RECLAMO.value
            elif any(word in mensaje_lower for word in ['hola', 'buenos', 'buenas', 'saludos']):
                return IntentType.SALUDO.value
            elif any(word in mensaje_lower for word in ['adios', 'gracias', 'hasta luego']):
                return IntentType.DESPEDIDA.value
            else:
                return IntentType.OTRO.value
                
        except Exception as e:
            logger.error(f"Error clasificando intent: {e}")
            return IntentType.OTRO.value
    
    def _estimate_token_count(self, user_message: str, bot_response: str) -> int:
        """Estima el número de tokens usando conteo de palabras"""
        try:
            # Estimación simple: ~1.3 tokens por palabra en español
            user_words = len(user_message.split())
            bot_words = len(bot_response.split())
            return int((user_words + bot_words) * 1.3)
        except:
            return 0
    
    def _record_message_metrics(
        self,
        session_id,
        user_message: str,
        bot_response: str,
        sentiment: str,
        sentiment_confidence: float,
        intent: str,
        processing_time_ms: float,
        token_count: int,
        detected_entities=None,
        is_escalation_request: bool = False
    ):
        """Registra métricas del mensaje"""
        try:
            # Mapear sentimiento a enum
            sentiment_mapped = sentiment if sentiment in [s.value for s in SentimentType] else SentimentType.NEUTRAL.value
            
            self.metrics_collector.record_message_sync(
                session_id=session_id,
                user_message=user_message,
                bot_response=bot_response,
                sentiment=sentiment_mapped,
                sentiment_confidence=sentiment_confidence,
                intent=intent,
                intent_confidence=0.8,  # Valor por defecto para clasificación simple
                processing_time_ms=processing_time_ms,
                token_count=token_count,
                is_escalation_request=is_escalation_request,
                detected_entities=detected_entities or {},
                response_tone="amigable"
            )
        except Exception as e:
            logger.error(f"Error recording message metrics: {e}")
    
    def _record_escalation_metrics(
        self,
        session_id,
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
                token_count=self._estimate_token_count(user_message, bot_response),
                is_escalation_request=True,
                response_tone="comprensivo"
            )
        except Exception as e:
            logger.error(f"Error recording escalation metrics: {e}")
    
    def _record_error_metrics(
        self,
        session_id,
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
                token_count=len(user_message.split()) * 2,  # Estimación simple
                is_escalation_request=False,
                response_tone="disculpa"
            )
        except Exception as e:
            logger.error(f"Error recording error metrics: {e}")
    
    # NUEVO MÉTODO: Para notificar a los agentes de un nuevo mensaje
    def _notificar_agente_nuevo_mensaje(self, usuario_id: str, mensaje: str) -> None:
        """
        Notifica a los agentes asignados que hay un nuevo mensaje del usuario.
        
        Args:
            usuario_id: ID del usuario
            mensaje: Contenido del mensaje
        """
        try:
            # Verificar si existe el servicio de notificación por WebSocket
            if not hasattr(self.chatbot_service, 'support_repository'):
                logger.warning("No hay repositorio de soporte disponible para la notificación")
                return
                
            support_repo = self.chatbot_service.support_repository
            
            # Importar dinámicamente para evitar dependencias circulares
            try:
                from bot_siacasa.infrastructure.websocket.socketio_server import get_socketio_server
                
                # Intentar obtener servidor SocketIO
                socketio_server = get_socketio_server()
                
                # Si no hay servidores disponibles, salir
                if not socketio_server:
                    logger.warning("No hay servidor SocketIO disponible para notificación")
                    return
                
                # Obtener tickets activos del usuario
                tickets = support_repo.obtener_tickets_por_usuario(usuario_id)
                active_tickets = [t for t in tickets if t.estado.value in ['pending', 'assigned', 'active']]
                
                if not active_tickets:
                    logger.warning(f"No se encontraron tickets activos para el usuario {usuario_id}")
                    return
                
                # Tomar el ticket más reciente
                ticket = active_tickets[0]
                
                # Datos del mensaje para la notificación
                message_data = {
                    'type': 'chat_message',
                    'ticket_id': ticket.id,
                    'content': mensaje,
                    'sender_id': usuario_id,
                    'sender_name': ticket.usuario.nombre or "Usuario",
                    'sender_type': 'user',
                    'is_internal': False,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Emitir mensaje a través del SocketIO
                if hasattr(socketio_server, 'socketio'):
                    logger.info(f"Notificando vía SocketIO: ticket {ticket.id}, mensaje del usuario {usuario_id}")
                    
                    # Usar SocketIO para notificar
                    ticket_room = f'ticket_{ticket.id}'
                    socketio_server.socketio.emit('chat_message', message_data, room=ticket_room)
                    
                    # Si el ticket tiene un agente asignado, notificarle directamente
                    if ticket.agente_id and ticket.agente_id in socketio_server.agent_connections:
                        agent_sid = socketio_server.agent_connections[ticket.agente_id]
                        socketio_server.socketio.emit('new_user_message', message_data, room=agent_sid)
                
                logger.info(f"Notificación enviada para el ticket {ticket.id}")
                
            except ImportError as e:
                logger.error(f"Error al importar módulos WebSocket: {e}")
            except Exception as e:
                logger.error(f"Error en notificación WebSocket: {e}", exc_info=True)
                
        except Exception as e:
            logger.error(f"Error al notificar a agentes: {e}", exc_info=True)