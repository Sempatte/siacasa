from dataclasses import dataclass
from typing import List, Optional, Dict

@dataclass
class AnalisisSentimiento:
    """Entidad que representa el análisis de sentimiento de un mensaje."""
    sentimiento: str         # "positivo", "negativo", o "neutral"
    confianza: float         # Valor de 0 a 1 que indica la confianza del análisis
    emociones: List[str]     # Lista de emociones detectadas
    metadata: Optional[Dict] = None  # Metadatos adicionales del análisis
    
    def to_dict(self) -> Dict:
        """Convierte el análisis a un diccionario."""
        return {
            "sentimiento": self.sentimiento,
            "confianza": self.confianza,
            "emociones": self.emociones,
            "metadata": self.metadata or {}
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AnalisisSentimiento':
        """Crea un objeto AnalisisSentimiento a partir de un diccionario."""
        return cls(
            sentimiento=data.get("sentimiento", "neutral"),
            confianza=data.get("confianza", 0.5),
            emociones=data.get("emociones", []),
            metadata=data.get("metadata")
        )
    
    @classmethod
    def default(cls) -> 'AnalisisSentimiento':
        """Crea un objeto AnalisisSentimiento con valores por defecto."""
        return cls(
            sentimiento="neutral",
            confianza=0.5,
            emociones=[],
            metadata=None
        )