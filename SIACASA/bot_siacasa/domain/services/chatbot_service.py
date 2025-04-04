import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, TYPE_CHECKING

from bot_siacasa.domain.entities.mensaje import Mensaje
from bot_siacasa.domain.entities.usuario import Usuario
from bot_siacasa.domain.entities.conversacion import Conversacion
from bot_siacasa.domain.entities.analisis_sentimiento import AnalisisSentimiento
from bot_siacasa.application.interfaces.repository_interface import IRepository

# Evitar importación circular
if TYPE_CHECKING:
    from bot_siacasa.application.use_cases.analizar_sentimiento_use_case import AnalizarSentimientoUseCase

logger = logging.getLogger(__name__)

class ChatbotService:
    """
    Servicio principal del chatbot que implementa la lógica de negocio.
    """
    
    def __init__(self, repository: IRepository, sentimiento_analyzer):
        """
        Inicializa el servicio del chatbot.
        
        Args:
            repository: Repositorio para almacenar datos
            sentimiento_analyzer: Analizador de sentimientos
        """
        self.repository = repository
        self.sentimiento_analyzer = sentimiento_analyzer
        
        # Mensaje de sistema que define el comportamiento del chatbot
        self.mensaje_sistema = Mensaje(
            role="system",
            content="""
            Eres SIACASA, un asistente bancario virtual diseñado para brindar atención al cliente 
            en el sector bancario peruano. Tu objetivo es proporcionar respuestas precisas, 
            eficientes y empáticas a las consultas de los clientes.
            
            - Debes ser amable, respetuoso y profesional en todo momento.
            - Adapta tu tono según el estado emocional del cliente.
            - Proporciona información clara sobre productos y servicios bancarios.
            - Ayuda a resolver problemas comunes como consultas de saldo, transferencias, etc.
            - Si no puedes resolver una consulta, ofrece derivar al cliente con un agente humano.
            - Respeta la privacidad y seguridad de los datos del cliente.
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