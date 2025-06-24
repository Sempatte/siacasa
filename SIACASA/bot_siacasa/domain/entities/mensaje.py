# bot_siacasa/domain/entities/mensaje.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List
import uuid

@dataclass
class Mensaje:
    """Entidad que representa un mensaje en la conversación."""
    role: str                # "user", "system", o "assistant"
    content: str             # Contenido del mensaje
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Optional[Dict] = None
    
    # Campos adicionales que coinciden con tu DB
    id: Optional[str] = field(default_factory=lambda: str(uuid.uuid4()))
    conversacion_id: Optional[str] = None
    sentiment_score: Optional[float] = None
    processing_time_ms: Optional[float] = None
    ai_processing_time_ms: Optional[float] = None
    sentiment: Optional[str] = None
    sentiment_confidence: Optional[float] = None
    intent: Optional[str] = None
    intent_confidence: Optional[float] = None
    token_count: Optional[int] = None
    is_escalation_request: bool = False
    response_tone: Optional[str] = None