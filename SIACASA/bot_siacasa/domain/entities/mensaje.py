# bot_siacasa/domain/entities/mensaje.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, List

@dataclass
class Mensaje:
    """Entidad que representa un mensaje en la conversación."""
    role: str                # "user", "system", o "assistant"
    content: str             # Contenido del mensaje
    timestamp: datetime = datetime.now()  # Momento en que se creó el mensaje
    metadata: Optional[Dict] = None  # Metadatos adicionales (ej. sentimiento)
