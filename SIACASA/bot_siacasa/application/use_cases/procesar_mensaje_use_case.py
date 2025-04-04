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
            
            # Registrar el mensaje
            logger.info(f"Mensaje recibido de {usuario_id}: {mensaje_usuario}")
            
            # Actualizar información del usuario si se proporciona
            if info_usuario:
                self.chatbot_service.actualizar_datos_usuario(usuario_id, info_usuario)
            
            # Agregar el mensaje del usuario a la conversación
            self.chatbot_service.agregar_mensaje_usuario(usuario_id, mensaje_usuario)
            
            # Analizar el sentimiento del mensaje
            datos_sentimiento = self.chatbot_service.analizar_sentimiento_mensaje(mensaje_usuario)
            
            # Generar instrucciones adicionales basadas en el sentimiento
            instrucciones_adicionales = f"""
            Información sobre el sentimiento detectado en el último mensaje del usuario:
            - Sentimiento general: {datos_sentimiento.sentimiento}
            - Nivel de confianza: {datos_sentimiento.confianza}
            - Emociones detectadas: {', '.join(datos_sentimiento.emociones)}
            
            Adapta tu respuesta al estado emocional del cliente. Si está molesto o frustrado,
            muestra más empatía y comprensión. Si está confundido, sé más claro y didáctico.
            Si está satisfecho, mantén un tono positivo y cordial.
            """
            
            # Obtener el historial de mensajes
            mensajes = self.chatbot_service.obtener_historial_mensajes(usuario_id)
            
            # Generar respuesta con el modelo de IA
            respuesta = self.ai_provider.generar_respuesta(mensajes, instrucciones_adicionales)
            
            # Agregar la respuesta del asistente a la conversación
            self.chatbot_service.agregar_mensaje_asistente(usuario_id, respuesta)
            
            # Registrar la respuesta
            logger.info(f"Respuesta enviada a {usuario_id}: {respuesta}")
            
            return respuesta
            
        except Exception as e:
            logger.error(f"Error al procesar mensaje: {e}")
            return "Lo siento, ocurrió un error al procesar tu mensaje. Por favor, inténtalo de nuevo."