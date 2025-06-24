# bot_siacasa/domain/entities/analisis_sentimiento.py
from dataclasses import dataclass
from typing import List, Optional, Dict

@dataclass
class AnalisisSentimiento:
    """Entidad que representa el análisis completo de sentimiento de un mensaje."""
    # Campos principales
    sentimiento: str         # "positivo", "negativo", o "neutral"
    confianza: float         # Valor de 0 a 1 que indica la confianza del análisis
    emociones: List[str]     # Lista de emociones detectadas
    
    # Campos adicionales para análisis completo
    intent: Optional[str] = None              # Intent detectado
    intent_confidence: Optional[float] = None  # Confianza del intent
    entidades: Optional[Dict] = None          # Entidades extraídas
    escalacion_requerida: bool = False        # Si requiere escalación
    tono_sugerido: Optional[str] = None       # Tono sugerido para respuesta
    metadata: Optional[Dict] = None           # Metadatos adicionales del análisis
    
    def to_dict(self) -> Dict:
        """Convierte el análisis a un diccionario."""
        return {
            "sentimiento": self.sentimiento,
            "confianza": self.confianza,
            "emociones": self.emociones,
            "intent": self.intent,
            "intent_confidence": self.intent_confidence,
            "entidades": self.entidades or {},
            "escalacion_requerida": self.escalacion_requerida,
            "tono_sugerido": self.tono_sugerido,
            "metadata": self.metadata or {}
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AnalisisSentimiento':
        """Crea un objeto AnalisisSentimiento a partir de un diccionario."""
        return cls(
            sentimiento=data.get("sentimiento", "neutral"),
            confianza=data.get("confianza", 0.5),
            emociones=data.get("emociones", []),
            intent=data.get("intent"),
            intent_confidence=data.get("intent_confidence"),
            entidades=data.get("entidades"),
            escalacion_requerida=data.get("escalacion_requerida", False),
            tono_sugerido=data.get("tono_sugerido"),
            metadata=data.get("metadata")
        )
    
    @classmethod
    def default(cls) -> 'AnalisisSentimiento':
        """Crea un objeto AnalisisSentimiento con valores por defecto."""
        return cls(
            sentimiento="neutral",
            confianza=0.5,
            emociones=[],
            intent="consulta_general",
            intent_confidence=0.5,
            entidades={},
            escalacion_requerida=False,
            tono_sugerido="profesional",
            metadata=None
        )