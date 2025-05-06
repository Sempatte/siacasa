from dataclasses import dataclass
from typing import Dict, Optional, List

@dataclass
class Usuario:
    """Entidad que representa a un usuario del chatbot."""
    id: str                  # Identificador único del usuario
    nombre: Optional[str] = None  # Nombre del usuario (si está disponible)
    datos: Dict = None       # Datos adicionales del usuario
    preferencias: Dict = None  # Preferencias del usuario
    
    def __post_init__(self):
        if self.datos is None:
            self.datos = {}
        if self.preferencias is None:
            self.preferencias = {}