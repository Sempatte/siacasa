import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, TYPE_CHECKING

from bot_siacasa.domain.entities.mensaje import Mensaje
from bot_siacasa.domain.entities.usuario import Usuario
from bot_siacasa.domain.entities.conversacion import Conversacion
from bot_siacasa.domain.entities.analisis_sentimiento import AnalisisSentimiento
from bot_siacasa.domain.entities.ticket import Ticket, TicketStatus, EscalationReason
from bot_siacasa.application.interfaces.repository_interface import IRepository
from bot_siacasa.domain.services.escalation_service import EscalationService

# Evitar importación circular
if TYPE_CHECKING:
    from bot_siacasa.application.use_cases.analizar_sentimiento_use_case import (
        AnalizarSentimientoUseCase,
    )

logger = logging.getLogger(__name__)


class ChatbotService:
    """
    Servicio principal del chatbot que implementa la lógica de negocio.
    """

   # Modificación para el constructor de ChatbotService
    def __init__(
        self, repository: IRepository, sentimiento_analyzer, ai_provider=None, bank_config=None,
        support_repository=None
    ):
        """
        Inicializa el servicio del chatbot.

        Args:
            repository: Repositorio para almacenar datos
            sentimiento_analyzer: Analizador de sentimientos
            ai_provider: Proveedor de IA para generar respuestas
            bank_config: Configuración específica del banco
            support_repository: Repositorio para tickets de soporte (opcional)
        """
        self.repository = repository
        self.sentimiento_analyzer = sentimiento_analyzer
        self.ai_provider = ai_provider  # Añadimos el proveedor de IA
        self.support_repository = support_repository  # Repositorio para tickets de soporte
        default_config = {
                "bank_name": "Banco",
                "greeting": "Hola, soy SIACASA, tu asistente bancario virtual.",
                "style": "formal"
            }
        
        self.escalation_service = None
        if support_repository:
            self.escalation_service = EscalationService(support_repository)
            logger.info("Escalation service initialized successfully")
        else:
            logger.warning("Support repository not provided, escalation service not initialized")
        self.bank_config = {**default_config, **(bank_config or {})}
        # Mensaje de sistema que define el comportamiento del chatbot
        self.mensaje_sistema = Mensaje(
            role="system",
            content=f"""
            Eres SIACASA, un asistente bancario virtual diseñado para brindar atención al cliente 
            del {self.bank_config['bank_name']}. Tu objetivo es proporcionar respuestas precisas, 
            eficientes y empáticas a las consultas de los clientes.
            
            - Identifícate como asistente virtual del {self.bank_config['bank_name']}.
            - Debes ser amable, respetuoso y profesional en todo momento.
            - Adapta tu tono según el estado emocional del cliente.
            - Proporciona información clara sobre productos y servicios bancarios.
            - Ayuda a resolver problemas comunes como consultas de saldo, transferencias, etc.
            - Si no puedes resolver una consulta, ofrece derivar al cliente con un agente humano.
            - Recuerda los ultimos mensajes de la conversación para mantener el contexto.
            - Si el cliente está molesto o frustrado, muestra empatía y ofrece soluciones.
            - Si el cliente está satisfecho, agradece su confianza y ofrécele más ayuda.
            - Si el cliente está confundido, sé claro y didáctico en tus explicaciones.
            - No vuelvas a saludar al cliente en cada respuesta.
            - No uses jerga técnica o términos complicados.
            - Utiliza un lenguaje sencillo evitando tecnicismos cuando sea posible.
            """
        )

        

    def obtener_o_crear_conversacion(self, usuario_id: str) -> Conversacion:
        """
        Obtiene una conversación existente o crea una nueva.

        Args:
            usuario_id: ID del usuario

        Returns:
            Conversación activa
        """
        # Intentar obtener una conversación existente
        conversacion = self.repository.obtener_conversacion_activa(usuario_id)

        # Si no existe, crear una nueva
        if not conversacion:
            # Obtener o crear usuario
            usuario = self.repository.obtener_usuario(usuario_id)
            if not usuario:
                usuario = Usuario(id=usuario_id)
                self.repository.guardar_usuario(usuario)

            # Crear nueva conversación
            conversacion_id = str(uuid.uuid4())
            conversacion = Conversacion(id=conversacion_id, usuario=usuario)

            # Agregar mensaje del sistema
            conversacion.agregar_mensaje(self.mensaje_sistema)

            # Guardar la conversación
            self.repository.guardar_conversacion(conversacion)

        return conversacion

    def agregar_mensaje_usuario(self, usuario_id: str, texto: str) -> Mensaje:
        """
        Agrega un mensaje del usuario a la conversación.

        Args:
            usuario_id: ID del usuario
            texto: Texto del mensaje

        Returns:
            Mensaje creado
        """
        conversacion = self.obtener_o_crear_conversacion(usuario_id)

        # Crear mensaje
        mensaje = Mensaje(role="user", content=texto)

        # Agregar a la conversación
        conversacion.agregar_mensaje(mensaje)

        # Limitar historial para evitar tokens excesivos
        conversacion.limitar_historial(max_mensajes=20)

        # Guardar la conversación actualizada
        self.repository.guardar_conversacion(conversacion)

        return mensaje

    def agregar_mensaje_asistente(self, usuario_id: str, texto: str) -> Mensaje:
        """
        Agrega un mensaje del asistente a la conversación.

        Args:
            usuario_id: ID del usuario
            texto: Texto del mensaje

        Returns:
            Mensaje creado
        """
        conversacion = self.obtener_o_crear_conversacion(usuario_id)

        # Crear mensaje
        mensaje = Mensaje(role="assistant", content=texto)

        # Agregar a la conversación
        conversacion.agregar_mensaje(mensaje)

        # Guardar la conversación actualizada
        self.repository.guardar_conversacion(conversacion)

        return mensaje
    
    # Nuevo método en ChatbotService
    def obtener_resumen_conversacion(self, usuario_id: str) -> str:
        """Genera un resumen de la conversación para mantener contexto."""
        conversacion = self.obtener_o_crear_conversacion(usuario_id)
        # Si hay pocos mensajes, no es necesario resumir
        if len(conversacion.mensajes) < 15:
            return ""
        
        # Solicitar un resumen a la IA
        mensajes_para_resumir = conversacion.mensajes[-15:]  # Últimos 15 mensajes
        mensajes_formateados = [f"{m.role}: {m.content}" for m in mensajes_para_resumir]
        
        instruccion = "Resume brevemente los siguientes intercambios de la conversación manteniendo los puntos clave:"
        contenido = "\n".join(mensajes_formateados)
        
        mensajes_resumen = [
            {"role": "system", "content": instruccion},
            {"role": "user", "content": contenido}
        ]
        
        respuesta = self.ai_provider.generar_respuesta(mensajes_resumen)
        return respuesta

    def obtener_historial_mensajes(self, usuario_id: str) -> List[Dict[str, str]]:
        """
        Obtiene el historial de mensajes de la conversación en formato para OpenAI.

        Args:
            usuario_id: ID del usuario

        Returns:
            Lista de mensajes en formato para la API de OpenAI
        """
        conversacion = self.obtener_o_crear_conversacion(usuario_id)
        return conversacion.obtener_historial()

    def actualizar_datos_usuario(self, usuario_id: str, datos: Dict) -> None:
        """
        Actualiza los datos del usuario.

        Args:
            usuario_id: ID del usuario
            datos: Datos a actualizar
        """
        usuario = self.repository.obtener_usuario(usuario_id)
        if usuario:
            usuario.datos.update(datos)
            self.repository.guardar_usuario(usuario)

    def analizar_sentimiento_mensaje(self, texto: str) -> AnalisisSentimiento:
        """
        Analiza el sentimiento de un mensaje.

        Args:
            texto: Texto a analizar

        Returns:
            Análisis de sentimiento
        """
        return self.sentimiento_analyzer.execute(texto)
    
    def check_for_escalation(self, mensaje_usuario: str, usuario_id: str) -> bool:
        """
        Verifica si es necesario escalar la conversación a un humano.
        
        Args:
            mensaje_usuario: Texto del mensaje del usuario
            usuario_id: ID del usuario
            
        Returns:
            True si es necesario escalar, False en caso contrario
        """
        # Si no hay servicio de escalación, no se puede escalar
        if not self.escalation_service:
            logger.warning("Escalation service not initialized, cannot escalate")
            return False
        
        # Obtener conversación activa
        conversacion = self.obtener_o_crear_conversacion(usuario_id)
        
        # Verificar si debe escalar
        should_escalate, reason = self.escalation_service.check_for_escalation(mensaje_usuario, conversacion)
        
        # Si debe escalar, crear ticket
        if should_escalate and reason:
            # Obtener usuario
            usuario = self.repository.obtener_usuario(usuario_id)
            
            # Crear ticket
            ticket = self.escalation_service.create_ticket(conversacion, usuario, reason)
            
            logger.info(f"Conversación escalada a humano. Ticket creado: {ticket.id}")
            return True
        
        return False
    
    def esta_escalada(self, usuario_id: str) -> bool:
        """
        Verifica si la conversación ya ha sido escalada a un humano.
        
        Args:
            usuario_id: ID del usuario
            
        Returns:
            True si ya está escalada, False en caso contrario
        """
        # Si no hay servicio de escalación, no está escalada
        if not self.escalation_service:
            return False
        
        # Buscar tickets activos para este usuario
        if hasattr(self.escalation_service.repository, 'obtener_tickets_por_usuario'):
            tickets = self.escalation_service.repository.obtener_tickets_por_usuario(usuario_id)
            
            # Verificar si hay algún ticket activo (pendiente, asignado o activo)
            for ticket in tickets:
                if ticket.estado in [TicketStatus.PENDING, TicketStatus.ASSIGNED, TicketStatus.ACTIVE]:
                    return True
        
        return False

      
    