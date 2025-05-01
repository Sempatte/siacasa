from abc import ABC, abstractmethod
from typing import Optional, List, TYPE_CHECKING

# Evitar importaciones circulares
if TYPE_CHECKING:
    from bot_siacasa.domain.entities.usuario import Usuario
    from bot_siacasa.domain.entities.conversacion import Conversacion

class IRepository(ABC):
    """
    Interfaz para repositorios de datos.
    Define los métodos que cualquier implementación de repositorio debe proporcionar.
    """
    
    @abstractmethod
    def guardar_usuario(self, usuario: "Usuario") -> None:
        """
        Guarda un usuario en el repositorio.
        
        Args:
            usuario: Usuario a guardar
        """
        pass
    
    @abstractmethod
    def obtener_usuario(self, usuario_id: str) -> Optional["Usuario"]:
        """
        Obtiene un usuario por su ID.
        
        Args:
            usuario_id: ID del usuario
            
        Returns:
            Usuario o None si no existe
        """
        pass
    
    @abstractmethod
    def guardar_conversacion(self, conversacion: "Conversacion") -> None:
        """
        Guarda una conversación en el repositorio.
        
        Args:
            conversacion: Conversación a guardar
        """
        pass
    
    @abstractmethod
    def obtener_conversacion(self, conversacion_id: str) -> Optional["Conversacion"]:
        """
        Obtiene una conversación por su ID.
        
        Args:
            conversacion_id: ID de la conversación
            
        Returns:
            Conversación o None si no existe
        """
        pass
    
    @abstractmethod
    def obtener_conversacion_activa(self, usuario_id: str) -> Optional["Conversacion"]:
        """
        Obtiene la conversación activa de un usuario.
        
        Args:
            usuario_id: ID del usuario
            
        Returns:
            Conversación activa o None si no existe
        """
        pass
    
    @abstractmethod
    def obtener_conversaciones_usuario(self, usuario_id: str) -> List["Conversacion"]:
        """
        Obtiene todas las conversaciones de un usuario.
        
        Args:
            usuario_id: ID del usuario
            
        Returns:
            Lista de conversaciones
        """
        pass