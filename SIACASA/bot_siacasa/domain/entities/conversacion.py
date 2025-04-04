from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional

from bot_siacasa.domain.entities.mensaje import Mensaje
from bot_siacasa.domain.entities.usuario import Usuario

@dataclass
class Conversacion:
    """Entidad que representa una conversación completa."""
    id: str                  # Identificador único de la conversación
    usuario: Usuario         # Usuario de la conversación
    mensajes: List[Mensaje] = field(default_factory=list)  # Lista de mensajes
    fecha_inicio: datetime = field(default_factory=datetime.now)  # Fecha de inicio de la conversación
    fecha_fin: Optional[datetime] = None  # Fecha de fin de la conversación (si ha terminado)
    metadata: Dict = field(default_factory=dict)  # Metadatos adicionales
    
    def agregar_mensaje(self, mensaje: Mensaje) -> None:
        """Agrega un mensaje a la conversación."""
        self.mensajes.append(mensaje)
    
    def obtener_historial(self) -> List[Dict[str, str]]:
        """Obtiene el historial de mensajes en formato para la API de OpenAI."""
        return [{"role": msg.role, "content": msg.content} for msg in self.mensajes]
    
    def limitar_historial(self, max_mensajes: int = 20) -> None:
        """Limita el historial de mensajes a un número máximo, manteniendo el primer mensaje del sistema."""
        if len(self.mensajes) > max_mensajes:
            # Buscar el primer mensaje del sistema
            primer_mensaje_sistema = next((msg for msg in self.mensajes if msg.role == "system"), None)
            
            if primer_mensaje_sistema:
                # Mantener el primer mensaje del sistema y los últimos (max_mensajes - 1) mensajes
                self.mensajes = [primer_mensaje_sistema] + self.mensajes[-(max_mensajes-1):]
            else:
                # Si no hay mensaje del sistema, simplemente mantener los últimos max_mensajes
                self.mensajes = self.mensajes[-max_mensajes:]