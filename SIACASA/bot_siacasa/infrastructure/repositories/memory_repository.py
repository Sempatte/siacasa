import logging
from typing import Dict, Optional, List
from datetime import datetime
import json

from bot_siacasa.application.interfaces.repository_interface import IRepository
from bot_siacasa.domain.entities.usuario import Usuario
from bot_siacasa.domain.entities.conversacion import Conversacion
from bot_siacasa.domain.entities.mensaje import Mensaje

logger = logging.getLogger(__name__)

class MemoryRepository(IRepository):
    """
    Implementación mejorada del repositorio en memoria.
    Incluye mejor manejo de errores y logging detallado.
    """
    
    def __init__(self):
        """
        Inicializa el repositorio en memoria.
        """
        self.usuarios: Dict[str, Usuario] = {}
        self.conversaciones: Dict[str, Conversacion] = {}
        self.conversaciones_activas: Dict[str, str] = {}  # usuario_id -> conversacion_id
        logger.info("Repositorio en memoria inicializado")
    
    def guardar_usuario(self, usuario: Usuario) -> None:
        """
        Guarda un usuario en el repositorio.
        
        Args:
            usuario: Usuario a guardar
        """
        try:
            self.usuarios[usuario.id] = usuario
            logger.info(f"Usuario guardado: {usuario.id}")
        except Exception as e:
            logger.error(f"Error al guardar usuario {usuario.id}: {e}", exc_info=True)
            raise
    
    def obtener_usuario(self, usuario_id: str) -> Optional[Usuario]:
        """
        Obtiene un usuario por su ID.
        
        Args:
            usuario_id: ID del usuario
            
        Returns:
            Usuario o None si no existe
        """
        try:
            usuario = self.usuarios.get(usuario_id)
            if usuario:
                logger.info(f"Usuario encontrado: {usuario_id}")
            else:
                logger.info(f"Usuario no encontrado: {usuario_id}")
            return usuario
        except Exception as e:
            logger.error(f"Error al obtener usuario {usuario_id}: {e}", exc_info=True)
            return None
    
    def guardar_conversacion(self, conversacion: Conversacion) -> None:
        """
        Guarda una conversación en el repositorio.
        
        Args:
            conversacion: Conversación a guardar
        """
        try:
            # Hacer una copia profunda para evitar problemas de referencia
            self.conversaciones[conversacion.id] = conversacion
            
            # Marcar como conversación activa para el usuario
            self.conversaciones_activas[conversacion.usuario.id] = conversacion.id
            
            # Log detallado
            num_mensajes = len(conversacion.mensajes) if hasattr(conversacion, 'mensajes') else 0
            logger.info(f"Conversación guardada: {conversacion.id} para usuario {conversacion.usuario.id} con {num_mensajes} mensajes")
            
            # Log de verificación de los mensajes
            if hasattr(conversacion, 'mensajes') and conversacion.mensajes:
                for i, msg in enumerate(conversacion.mensajes[-3:]):  # Solo los últimos 3
                    logger.debug(f"Mensaje #{i}: {msg.role} - {msg.content[:30]}...")
        except Exception as e:
            logger.error(f"Error al guardar conversación {conversacion.id}: {e}", exc_info=True)
            raise
    
    def obtener_conversacion(self, conversacion_id: str) -> Optional[Conversacion]:
        """
        Obtiene una conversación por su ID.
        
        Args:
            conversacion_id: ID de la conversación
            
        Returns:
            Conversación o None si no existe
        """
        try:
            conversacion = self.conversaciones.get(conversacion_id)
            if conversacion:
                num_mensajes = len(conversacion.mensajes) if hasattr(conversacion, 'mensajes') else 0
                logger.info(f"Conversación encontrada: {conversacion_id} con {num_mensajes} mensajes")
            else:
                logger.info(f"Conversación no encontrada: {conversacion_id}")
            return conversacion
        except Exception as e:
            logger.error(f"Error al obtener conversación {conversacion_id}: {e}", exc_info=True)
            return None
    
    def obtener_conversacion_activa(self, usuario_id: str) -> Optional[Conversacion]:
        """
        Obtiene la conversación activa de un usuario.
        
        Args:
            usuario_id: ID del usuario
            
        Returns:
            Conversación activa o None si no existe
        """
        try:
            # Obtener ID de la conversación activa
            conversacion_id = self.conversaciones_activas.get(usuario_id)
            
            if not conversacion_id:
                logger.info(f"Usuario {usuario_id} no tiene conversación activa")
                return None
            
            # Obtener la conversación
            conversacion = self.conversaciones.get(conversacion_id)
            
            if conversacion:
                num_mensajes = len(conversacion.mensajes) if hasattr(conversacion, 'mensajes') else 0
                logger.info(f"Conversación activa encontrada para usuario {usuario_id}: {conversacion_id} con {num_mensajes} mensajes")
                
                # Verificar mensajes
                if hasattr(conversacion, 'mensajes') and conversacion.mensajes:
                    roles = [msg.role for msg in conversacion.mensajes]
                    logger.debug(f"Roles de mensajes en la conversación: {roles}")
            else:
                logger.warning(f"ID de conversación activa {conversacion_id} para usuario {usuario_id} no encontrado")
                
                # Limpiar la referencia inválida
                del self.conversaciones_activas[usuario_id]
            
            return conversacion
        except Exception as e:
            logger.error(f"Error al obtener conversación activa para usuario {usuario_id}: {e}", exc_info=True)
            return None
    
    def obtener_conversaciones_usuario(self, usuario_id: str) -> List[Conversacion]:
        """
        Obtiene todas las conversaciones de un usuario.
        
        Args:
            usuario_id: ID del usuario
            
        Returns:
            Lista de conversaciones
        """
        try:
            conversaciones = [
                conversacion for conversacion in self.conversaciones.values()
                if conversacion.usuario.id == usuario_id
            ]
            
            logger.info(f"Obtenidas {len(conversaciones)} conversaciones para usuario {usuario_id}")
            return conversaciones
        except Exception as e:
            logger.error(f"Error al obtener conversaciones para usuario {usuario_id}: {e}", exc_info=True)
            return []
    
    def finalizar_conversacion(self, conversacion_id: str) -> None:
        """
        Finaliza una conversación.
        
        Args:
            conversacion_id: ID de la conversación
        """
        try:
            # Obtener la conversación
            conversacion = self.conversaciones.get(conversacion_id)
            
            if not conversacion:
                logger.warning(f"Intento de finalizar conversación inexistente: {conversacion_id}")
                return
            
            # Marcar como finalizada
            conversacion.fecha_fin = datetime.now()
            
            # Actualizar en el repositorio
            self.conversaciones[conversacion_id] = conversacion
            
            # Eliminar como conversación activa
            usuario_id = conversacion.usuario.id
            if usuario_id in self.conversaciones_activas and self.conversaciones_activas[usuario_id] == conversacion_id:
                del self.conversaciones_activas[usuario_id]
            
            logger.info(f"Conversación {conversacion_id} finalizada para usuario {usuario_id}")
        except Exception as e:
            logger.error(f"Error al finalizar conversación {conversacion_id}: {e}", exc_info=True)
    
    # Método adicional para depuración
    def debug_status(self) -> Dict:
        """
        Devuelve información de depuración sobre el estado del repositorio.
        
        Returns:
            Diccionario con información de estado
        """
        try:
            status = {
                "usuarios": len(self.usuarios),
                "conversaciones": len(self.conversaciones),
                "conversaciones_activas": len(self.conversaciones_activas),
                "detalle_usuarios": [],
                "detalle_conversaciones": []
            }
            
            # Información de usuarios
            for usuario_id, usuario in self.usuarios.items():
                status["detalle_usuarios"].append({
                    "id": usuario_id,
                    "datos": usuario.datos
                })
            
            # Información de conversaciones
            for conv_id, conv in self.conversaciones.items():
                num_mensajes = len(conv.mensajes) if hasattr(conv, 'mensajes') else 0
                status["detalle_conversaciones"].append({
                    "id": conv_id,
                    "usuario_id": conv.usuario.id,
                    "num_mensajes": num_mensajes,
                    "fecha_inicio": str(conv.fecha_inicio),
                    "fecha_fin": str(conv.fecha_fin) if conv.fecha_fin else None,
                    "activa": conv_id in self.conversaciones_activas.values()
                })
            
            return status
        except Exception as e:
            logger.error(f"Error al generar reporte de estado: {e}", exc_info=True)
            return {"error": str(e)}