from dataclasses import dataclass
from typing import List, Optional

@dataclass
class QueryAnalysis:
    """
    DTO para almacenar el resultado del análisis de la consulta de un usuario.
    """
    original_query: str
    sentiment: str  # e.g., "positivo", "negativo", "neutral"
    detected_entities: dict  # e.g., {"producto": "crédito agrario", "monto": "5000"}
    cleaned_query: str  # Consulta limpia o reformulada para la búsqueda semántica
    response_tone: str # Tono sugerido para la respuesta (ej. "empático y tranquilizador") 