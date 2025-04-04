# bot_siacasa/infrastructure/repositories/memory_repository.py
import logging
from typing import Dict, Optional, List
from datetime import datetime

from bot_siacasa.application.interfaces.repository_interface import IRepository
from bot_siacasa.domain.entities.usuario import Usuario
from bot_siacasa.domain.entities.conversacion import Conversacion

logger = logging.getLogger(__name__)

class MemoryRepository(IRepository):
    """
    Implementación de repositorio que almacena datos en memoria.
    
    Esta implementación es útil para desarrollo y pruebas. Para producción,
    se debería implementar una versión que utilice una base de datos persistente.
    """
    
    def __init__(self):
        """
        Inicializa el repositorio en memoria.
        """
        self.usuarios: Dict[str, Usuario] = {}
        self.conversaciones: Dict[str, Conversacion] = {}
        self.conversaciones_activas: Dict[str, str] = {}  # usuario_id -> conversacion_id
    
    def guardar_usuario(self, usuario: Usuario) -> None:
        """
        Guarda un usuario en el repositorio.
        
        Args:
            usuario: Usuario a guardar
        """
        self.usuarios[usuario.id] = usuario
        logger.debug(f"Usuario guardado: {usuario.id}")
    
    def obtener_usuario(self, usuario_id: str) -> Optional[Usuario]:
        """
        Obtiene un usuario por su ID.
        
        Args:
            usuario_id: ID del usuario
            
        Returns:
            Usuario o None si no existe
        """
        return self.usuarios.get(usuario_id)
    
    def guardar_conversacion(self, conversacion: Conversacion) -> None:
        """
        Guarda una conversación en el repositorio.
        
        Args:
            conversacion: Conversación a guardar
        """
        self.conversaciones[conversacion.id] = conversacion
        self.conversaciones_activas[conversacion.usuario.id] = conversacion.id
        logger.debug(f"Conversación guardada: {conversacion.id} para usuario {conversacion.usuario.id}")
    
    def obtener_conversacion(self, conversacion_id: str) -> Optional[Conversacion]:
        """
        Obtiene una conversación por su ID.
        
        Args:
            conversacion_id: ID de la conversación
            
        Returns:
            Conversación o None si no existe
        """
        return self.conversaciones.get(conversacion_id)
    
    def obtener_conversacion_activa(self, usuario_id: str) -> Optional[Conversacion]:
        """
        Obtiene la conversación activa de un usuario.
        
        Args:
            usuario_id: ID del usuario
            
        Returns:
            Conversación activa o None si no existe
        """
        conversacion_id = self.conversaciones_activas.get(usuario_id)
        if conversacion_id:
            return self.conversaciones.get(conversacion_id)
        return None
    
    def obtener_conversaciones_usuario(self, usuario_id: str) -> List[Conversacion]:
        """
        Obtiene todas las conversaciones de un usuario.
        
        Args:
            usuario_id: ID del usuario
            
        Returns:
            Lista de conversaciones
        """
        return [
            conversacion for conversacion in self.conversaciones.values()
            if conversacion.usuario.id == usuario_id
        ]
    
    def finalizar_conversacion(self, conversacion_id: str) -> None:
        """
        Finaliza una conversación.
        
        Args:
            conversacion_id: ID de la conversación
        """
        conversacion = self.conversaciones.get(conversacion_id)
        if conversacion:
            conversacion.fecha_fin = datetime.now()
            # Actualizar conversación
            self.conversaciones[conversacion_id] = conversacion
            
            # Si es la conversación activa, eliminarla
            if conversacion.usuario.id in self.conversaciones_activas:
                if self.conversaciones_activas[conversacion.usuario.id] == conversacion_id:
                    del self.conversaciones_activas[conversacion.usuario.id]
            
            logger.debug(f"Conversación finalizada: {conversacion_id}")