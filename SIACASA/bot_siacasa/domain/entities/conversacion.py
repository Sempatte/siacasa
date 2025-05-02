from dataclasses import dataclass, field
from datetime import datetime
import logging
from typing import List, Dict, Optional

from bot_siacasa.domain.entities.mensaje import Mensaje
from bot_siacasa.domain.entities.usuario import Usuario

logger = logging.getLogger(__name__)

@dataclass
class Conversacion:
    """Entidad que representa una conversación completa."""
    id: str                  # Identificador único de la conversación
    usuario: Usuario         # Usuario de la conversación
    mensajes: List[Mensaje] = field(default_factory=list)  # Lista de mensajes
    fecha_inicio: datetime = field(default_factory=datetime.now)  # Fecha de inicio de la conversación
    fecha_fin: Optional[datetime] = None  # Fecha de fin de la conversación (si ha terminado)
    fecha_ultima_actividad: datetime = field(default_factory=datetime.now)  # Fecha de última actividad
    metadata: Dict = field(default_factory=dict)  # Metadatos adicionales
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def agregar_mensaje(self, mensaje: Mensaje) -> None:
        """
        Agrega un mensaje a la conversación.
        
        Args:
            mensaje: Mensaje a agregar
        """
        # Agregar mensaje a la lista
        self.mensajes.append(mensaje)
        # Actualizar fecha de última actividad
        self.fecha_ultima_actividad = datetime.now()
        logger.debug(f"Mensaje agregado a conversación {self.id}: {mensaje.role} - {mensaje.content[:50]}...")

    def obtener_historial(self) -> List[Dict[str, str]]:
        """
        Obtiene el historial de mensajes en formato para modelos de IA.
        
        Returns:
            Lista de mensajes en formato {role, content}
        """
        # Verificar que hay mensajes
        if not self.mensajes:
            logger.warning(f"Conversación {self.id} no tiene mensajes")
            return []
        
        # Asegurar que el mensaje de sistema siempre esté al principio
        sistema_encontrado = False
        historial = []
        
        for mensaje in self.mensajes:
            # Validar que el rol sea válido
            if mensaje.role not in ["system", "user", "assistant"]:
                logger.warning(f"Mensaje con rol inválido ignorado: {mensaje.role}")
                continue
                
            # Si es mensaje de sistema y aún no hemos encontrado uno,
            # ponerlo al principio
            if mensaje.role == "system" and not sistema_encontrado:
                historial.insert(0, {
                    "role": mensaje.role,
                    "content": mensaje.content
                })
                sistema_encontrado = True
            # Si no es mensaje de sistema o ya tenemos uno, añadir al final
            elif mensaje.role != "system" or sistema_encontrado:
                historial.append({
                    "role": mensaje.role,
                    "content": mensaje.content
                })
        
        logger.info(f"Obtenido historial de conversación {self.id} con {len(historial)} mensajes")
        return historial

    def limitar_historial(self, max_mensajes: int = 20) -> None:
        """
        Limita el número de mensajes en la conversación.
        
        Args:
            max_mensajes: Número máximo de mensajes a mantener
        """
        # Si no hay suficientes mensajes, no hacer nada
        if len(self.mensajes) <= max_mensajes:
            return
        
        logger.info(f"Limitando historial de conversación {self.id} de {len(self.mensajes)} a {max_mensajes} mensajes")
        
        # Encontrar mensaje de sistema
        sistema_idx = None
        for i, msg in enumerate(self.mensajes):
            if msg.role == "system":
                sistema_idx = i
                break
        
        if sistema_idx is not None:
            # Preservar mensaje de sistema y los mensajes más recientes
            sistema_msg = self.mensajes[sistema_idx]
            self.mensajes = [sistema_msg] + self.mensajes[-(max_mensajes-1):]
            logger.debug(f"Historial limitado preservando mensaje de sistema")
        else:
            # Si no hay mensaje de sistema, mantener solo los más recientes
            self.mensajes = self.mensajes[-max_mensajes:]
            logger.debug(f"Historial limitado sin mensaje de sistema")
    
    def esta_activa(self) -> bool:
        """
        Verifica si la conversación está activa.
        
        Returns:
            True si la conversación está activa, False si no
        """
        return self.fecha_fin is None
    
    def finalizar(self) -> None:
        """Finaliza la conversación."""
        self.fecha_fin = datetime.now()
        logger.info(f"Conversación {self.id} finalizada")