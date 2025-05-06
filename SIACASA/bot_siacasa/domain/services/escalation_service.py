# bot_siacasa/domain/services/escalation_service.py
import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, List, Tuple

from bot_siacasa.domain.entities.ticket import Ticket, TicketStatus, EscalationReason
from bot_siacasa.domain.entities.mensaje import Mensaje
from bot_siacasa.domain.entities.usuario import Usuario
from bot_siacasa.domain.entities.conversacion import Conversacion

logger = logging.getLogger(__name__)

class EscalationService:
    """
    Servicio para gestionar la escalación de conversaciones a agentes humanos.
    """
    
    def __init__(self, repository, notification_service=None):
        """
        Inicializa el servicio de escalación.
        
        Args:
            repository: Repositorio para almacenar tickets
            notification_service: Servicio de notificaciones (opcional)
        """
        self.repository = repository
        self.notification_service = notification_service
        
        # Palabras clave que indican que el usuario quiere hablar con un humano
        self.human_request_keywords = [
            "hablar con humano",
            "hablar con persona",
            "hablar con agente",
            "hablar con un humano",
            "hablar con una persona",
            "hablar con un agente",
            "atención humana",
            "atención de una persona",
            "necesito un humano",
            "necesito una persona",
            "necesito un agente",
            "quiero hablar con un humano",
            "quiero hablar con una persona",
            "quiero hablar con un agente",
            "comuníqueme con un humano",
            "comunicarme con un humano",
            "comunicarme con una persona",
            "comunicarme con un agente",
            "transferir a humano",
            "transferir a persona",
            "transferir a agente",
            "agente real",
            "persona real",
            "humano real",
            "no entiendes",
            "no me entiendes",
            "no estás entendiendo",
            "no eres útil",
            "no me estás ayudando"
        ]
        
        # Umbral de intentos fallidos para escalación automática
        self.failure_threshold = 3
    
    def check_for_escalation(self, mensaje: str, conversacion: Conversacion) -> Tuple[bool, Optional[EscalationReason]]:
        """
        Verifica si una conversación debe ser escalada a un humano.
        
        Args:
            mensaje: Texto del mensaje del usuario
            conversacion: Conversación actual
            
        Returns:
            Tupla (escalate, reason) donde escalate es un booleano que indica si se debe escalar
            y reason es la razón de la escalación (o None si no se debe escalar)
        """
        # Verificar si el usuario solicitó explícitamente hablar con un humano
        mensaje_lower = mensaje.lower()
        for keyword in self.human_request_keywords:
            if keyword in mensaje_lower:
                logger.info(f"Escalación solicitada por el usuario. Keyword: '{keyword}'")
                return True, EscalationReason.USER_REQUESTED
        
        # Verificar si hay múltiples intentos fallidos consecutivos
        failure_count = self._count_consecutive_failures(conversacion)
        if failure_count >= self.failure_threshold:
            logger.info(f"Escalación por múltiples intentos fallidos: {failure_count}")
            return True, EscalationReason.MULTIPLE_FAILURES
            
        # No es necesario escalar
        return False, None
    
    def _count_consecutive_failures(self, conversacion: Conversacion) -> int:
        """
        Cuenta el número de intentos fallidos consecutivos.
        
        Args:
            conversacion: Conversación a analizar
            
        Returns:
            Número de intentos fallidos consecutivos
        """
        # Implementación simple: contar frases negativas consecutivas del usuario
        failure_count = 0
        negative_indicators = [
            "no es lo que pregunté", 
            "no entiendes", 
            "no es correcto", 
            "no es así",
            "no me entiendes", 
            "no estás entendiendo", 
            "no me estás ayudando",
            "no es útil",
            "no es lo que necesito",
            "eso no me sirve",
            "no es eso",
            "no es lo que busco",
            "no es eso lo que quiero",
            "no es cierto",
            "está mal"
        ]
        
        # Solo mirar los últimos 6 mensajes para identificar frustración reciente
        recent_messages = conversacion.mensajes[-6:] if len(conversacion.mensajes) > 6 else conversacion.mensajes
        
        for i, msg in enumerate(recent_messages):
            if msg.role == "user":
                # Verificar si el mensaje contiene indicadores de frustración
                msg_lower = msg.content.lower()
                for indicator in negative_indicators:
                    if indicator in msg_lower:
                        failure_count += 1
                        break
            else:
                # Reiniciar contador si el usuario no expresa frustración después de la respuesta del asistente
                failure_count = 0
                
        return failure_count
        
    # Modify the create_ticket method in bot_siacasa/domain/services/escalation_service.py
    def create_ticket(self, conversacion: Conversacion, usuario: Usuario, razon: EscalationReason) -> Ticket:
        """
        Crea un nuevo ticket de soporte.
        
        Args:
            conversacion: Conversación asociada al ticket
            usuario: Usuario que creó el ticket
            razon: Razón de la escalación
            
        Returns:
            Ticket creado
        """
        ticket_id = str(uuid.uuid4())
        
        # Determinar la prioridad del ticket
        prioridad = self._determine_priority(conversacion, razon)
        
        # NUEVO: Extraer el código del banco de los metadatos de la conversación
        bank_code = None
        if hasattr(conversacion, 'metadata') and conversacion.metadata:
            bank_code = conversacion.metadata.get('bank_code')
        
        # Create database session entry if needed
        try:
            # Check if conversation exists in database
            query = "SELECT id FROM chatbot_sessions WHERE id = %s"
            result = self.repository.db.fetch_one(query, (conversacion.id,))
            
            if not result:
                # Create session in database
                query = """
                INSERT INTO chatbot_sessions (
                    id, user_id, bank_code, start_time, message_count, metadata
                ) VALUES (
                    %s, %s, %s, %s, %s, %s
                )
                """
                
                # Extract bank code from metadata if available
                bank_code = "default"
                if hasattr(conversacion, 'metadata') and conversacion.metadata:
                    bank_code = conversacion.metadata.get('bank_code', "default")
                
                # Count messages
                message_count = len(conversacion.mensajes) if hasattr(conversacion, 'mensajes') else 0
                
                # Create metadata JSON
                import json
                metadata = json.dumps({
                    'created_by': 'escalation_service',
                    'from_memory_repository': True
                })
                
                # Execute query
                self.repository.db.execute(
                    query,
                    (
                        conversacion.id,
                        conversacion.usuario.id,
                        bank_code,
                        conversacion.fecha_inicio,
                        message_count,
                        metadata
                    )
                )
                
                logger.info(f"Created database session for conversation {conversacion.id}")
                logger.info(f"Session created with ID: {conversacion.id}, User ID: {conversacion.usuario.id}, Bank Code: {bank_code}, Message Count: {message_count}")
        except Exception as e:
            logger.error(f"Error creating database session for conversation: {e}", exc_info=True)
            raise
        
        # Crear el ticket
        ticket = Ticket(
            id=ticket_id,
            conversacion=conversacion,
            usuario=usuario,
            estado=TicketStatus.PENDING,
            razon_escalacion=razon,
            prioridad=prioridad,
            metadata={"bank_code": bank_code} if bank_code else {}  # Incluir el bank_code en los metadatos
        )
        
        # Guardar el ticket en el repositorio
        self.repository.guardar_ticket(ticket)
        
        # Enviar notificación de nuevo ticket
        if self.notification_service:
            self.notification_service.notificar_nuevo_ticket(ticket)
        
        # Agregar mensaje de sistema a la conversación indicando la escalación
        self._add_escalation_message(conversacion, razon)
        
        logger.info(f"Nuevo ticket creado: {ticket_id}, Razón: {razon.value}, Prioridad: {prioridad}")
        return ticket
    
    # Add this method to the EscalationService class in bot_siacasa/domain/services/escalation_service.py

    def _ensure_conversation_session_exists(self, conversacion):
        """
        Ensures that the conversation exists in the chatbot_sessions table before creating a ticket.
        
        Args:
            conversacion: Conversation to check
        
        Returns:
            True if session exists or was created, False otherwise
        """
        try:
            # Check if conversation exists in database
            query = "SELECT id FROM chatbot_sessions WHERE id = %s"
            result = self.repository.db.fetch_one(query, (conversacion.id,))
            
            if result:
                # Session already exists
                return True
            
            # Create session in database
            query = """
            INSERT INTO chatbot_sessions (
                id, user_id, bank_code, start_time, message_count, metadata
            ) VALUES (
                %s, %s, %s, %s, %s, %s
            )
            """
            
            # Extract bank code from metadata if available
            bank_code = "default"
            if hasattr(conversacion, 'metadata') and conversacion.metadata:
                bank_code = conversacion.metadata.get('bank_code', "default")
            
            # Count messages
            message_count = len(conversacion.mensajes) if hasattr(conversacion, 'mensajes') else 0
            
            # Create metadata JSON
            import json
            metadata = json.dumps({
                'created_by': 'escalation_service',
                'from_memory_repository': True
            })
            
            # Execute query
            self.repository.db.execute(
                query,
                (
                    conversacion.id,
                    conversacion.usuario.id,
                    bank_code,
                    conversacion.fecha_inicio,
                    message_count,
                    metadata
                )
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error ensuring conversation session exists: {e}", exc_info=True)
            return False
    
    def _determine_priority(self, conversacion: Conversacion, razon: EscalationReason) -> int:
        """
        Determina la prioridad del ticket basándose en la conversación y la razón.
        
        Args:
            conversacion: Conversación asociada al ticket
            razon: Razón de la escalación
            
        Returns:
            Prioridad (1-5)
        """
        # Prioridad base según la razón de escalación
        if razon == EscalationReason.USER_REQUESTED:
            priority = 3  # Prioridad media
        elif razon == EscalationReason.MULTIPLE_FAILURES:
            priority = 4  # Prioridad alta
        elif razon == EscalationReason.COMPLEX_QUERY:
            priority = 2  # Prioridad baja-media
        elif razon == EscalationReason.AGENT_DECISION:
            priority = 3  # Prioridad media
        else:
            priority = 2  # Prioridad por defecto
        
        # Ajustar según duración de la conversación y número de mensajes
        message_count = len(conversacion.mensajes)
        if message_count > 10:
            priority += 1  # Aumentar prioridad para conversaciones largas
        
        # Limitar a rango 1-5
        return max(1, min(5, priority))
    
    def _add_escalation_message(self, conversacion: Conversacion, razon: EscalationReason) -> None:
        """
        Añade un mensaje del sistema a la conversación indicando la escalación.
        
        Args:
            conversacion: Conversación a la que añadir el mensaje
            razon: Razón de la escalación
        """
        # Mensaje según la razón de escalación
        if razon == EscalationReason.USER_REQUESTED:
            message = "Tu solicitud de hablar con un agente humano ha sido registrada. Un agente te atenderá lo antes posible. Mientras tanto, puedes seguir escribiendo y tu mensaje será visible para el agente cuando se conecte."
        elif razon == EscalationReason.MULTIPLE_FAILURES:
            message = "Parece que estamos teniendo dificultades para resolver tu consulta. Te estamos conectando con un agente humano que podrá ayudarte mejor. Un agente te atenderá lo antes posible."
        elif razon == EscalationReason.COMPLEX_QUERY:
            message = "Tu consulta requiere atención especializada. Estamos redirigiendo tu conversación a un agente humano que podrá ayudarte. Un agente te atenderá lo antes posible."
        elif razon == EscalationReason.AGENT_DECISION:
            message = "Un agente ha decidido atender tu caso personalmente. Un agente te atenderá lo antes posible."
        else:
            message = "Tu conversación ha sido escalada a un agente humano. Un agente te atenderá lo antes posible."
        
        # Crear mensaje del sistema
        sistema_msg = Mensaje(
            role="system",
            content=message
        )
        
        # Agregar mensaje a la conversación
        conversacion.agregar_mensaje(sistema_msg)
        
        # Mensaje del asistente (chatbot) para mostrar al usuario
        asistente_msg = Mensaje(
            role="assistant",
            content=message
        )
        
        # Agregar mensaje a la conversación
        conversacion.agregar_mensaje(asistente_msg)