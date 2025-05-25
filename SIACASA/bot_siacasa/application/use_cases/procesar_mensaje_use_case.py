import logging
import uuid
from typing import Dict, Optional

from bot_siacasa.application.interfaces.ia_provider_interface import IAProviderInterface

logger = logging.getLogger(__name__)

class ProcesarMensajeUseCase:
    """
    Caso de uso principal para procesar mensajes del usuario.
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
        try:
            # Si no se proporciona ID de usuario, generar uno nuevo
            if not usuario_id:
                usuario_id = str(uuid.uuid4())
            
            # Mejorar el logging para depuración
            logger.info(f"Procesando mensaje para usuario {usuario_id}: {mensaje_usuario}")
            
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
                
                return "Tu mensaje ha sido recibido. Un agente humano te responderá en breve. Por favor, ten paciencia."
            
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
                # La conversación ha sido escalada ahora
                return "Tu consulta ha sido escalada a un agente humano. Un agente te atenderá lo antes posible. Mientras tanto, puedes seguir escribiendo y tu mensaje será visible para el agente cuando se conecte."
            
            # Analizar el sentimiento del mensaje
            datos_sentimiento = self.chatbot_service.analizar_sentimiento_mensaje(mensaje_usuario)
            
            # Obtener el historial COMPLETO de mensajes
            mensajes = self.chatbot_service.obtener_historial_mensajes(usuario_id)
            logger.info(f"Historial obtenido con {len(mensajes)} mensajes")
            
            # Log de los primeros mensajes para verificar formato
            for i, msg in enumerate(mensajes[:3]):  # Solo mostrar los primeros 3 para evitar logs gigantes
                logger.info(f"Mensaje #{i}: role={msg['role']}, content={msg['content'][:50]}...")
            
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
            
            # Registrar la respuesta
            logger.info(f"Respuesta enviada a {usuario_id}: {respuesta[:100]}...")
            
            return respuesta
            
        except Exception as e:
            logger.error(f"Error al procesar mensaje: {e}", exc_info=True)  # Incluir stack trace
            return "Lo siento, ocurrió un error al procesar tu mensaje. Por favor, inténtalo de nuevo."
    
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
                from bot_siacasa.infrastructure.websocket.socket_server import get_websocket_server
                from bot_siacasa.infrastructure.websocket.socketio_server import get_socketio_server
                
                # Intentar obtener servidor WebSocket o SocketIO
                websocket_server = get_websocket_server()
                socketio_server = get_socketio_server()
                
                # Si no hay servidores disponibles, salir
                if not websocket_server and not socketio_server:
                    logger.warning("No hay servidor WebSocket/SocketIO disponible para notificación")
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
                    'timestamp': datetime.now().isoformat() if 'datetime' in globals() else "ahora"
                }
                
                # Emitir mensaje a través del WebSocket o SocketIO
                if websocket_server:
                    logger.info(f"Notificando vía WebSocket: ticket {ticket.id}, mensaje del usuario {usuario_id}")
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(websocket_server.broadcast_message(
                            ticket.id, 
                            mensaje, 
                            usuario_id, 
                            ticket.usuario.nombre or "Usuario", 
                            'user',
                            False
                        ))
                    finally:
                        loop.close()
                
                elif socketio_server and hasattr(socketio_server, 'socketio'):
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