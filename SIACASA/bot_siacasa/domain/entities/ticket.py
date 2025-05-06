# bot_siacasa/domain/entities/ticket.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List
from enum import Enum

from bot_siacasa.domain.entities.usuario import Usuario
from bot_siacasa.domain.entities.conversacion import Conversacion

class TicketStatus(Enum):
    """Estados posibles para un ticket de soporte."""
    PENDING = "pending"         # Esperando atención
    ASSIGNED = "assigned"       # Asignado a un agente
    ACTIVE = "active"           # Chat activo con agente
    RESOLVED = "resolved"       # Resuelto
    CLOSED = "closed"           # Cerrado

class EscalationReason(Enum):
    """Razones para la escalación de un chat a humano."""
    USER_REQUESTED = "user_requested"       # El usuario solicitó hablar con un humano
    MULTIPLE_FAILURES = "multiple_failures" # Múltiples intentos fallidos
    COMPLEX_QUERY = "complex_query"         # Consulta demasiado compleja
    AGENT_DECISION = "agent_decision"       # Decisión del agente

@dataclass
class Ticket:
    """Entidad que representa un ticket de soporte (escalación a humano)."""
    id: str                                     # Identificador único del ticket
    conversacion: Conversacion                 # Conversación asociada al ticket
    usuario: Usuario                           # Usuario que creó el ticket
    estado: TicketStatus                       # Estado actual del ticket
    razon_escalacion: EscalationReason        # Razón de la escalación
    fecha_creacion: datetime = field(default_factory=datetime.now)  # Fecha de creación
    fecha_asignacion: Optional[datetime] = None  # Fecha de asignación a un agente
    fecha_resolucion: Optional[datetime] = None  # Fecha de resolución
    agente_id: Optional[str] = None            # ID del agente asignado
    agente_nombre: Optional[str] = None        # Nombre del agente asignado
    notas: Optional[str] = None                # Notas internas del ticket
    prioridad: int = 1                         # Prioridad (1-5, donde 5 es la más alta)
    metadata: Dict = field(default_factory=dict)  # Metadatos adicionales
    
    def asignar_agente(self, agente_id: str, agente_nombre: str) -> None:
        """
        Asigna el ticket a un agente.
        
        Args:
            agente_id: ID del agente
            agente_nombre: Nombre del agente
        """
        self.agente_id = agente_id
        self.agente_nombre = agente_nombre
        self.estado = TicketStatus.ASSIGNED
        self.fecha_asignacion = datetime.now()
    
    def iniciar_chat(self) -> None:
        """Inicia el chat con el agente."""
        self.estado = TicketStatus.ACTIVE
    
    def resolver(self, notas: Optional[str] = None) -> None:
        """
        Marca el ticket como resuelto.
        
        Args:
            notas: Notas opcionales sobre la resolución
        """
        self.estado = TicketStatus.RESOLVED
        self.fecha_resolucion = datetime.now()
        if notas:
            self.notas = notas
    
    def cerrar(self) -> None:
        """Cierra el ticket definitivamente."""
        self.estado = TicketStatus.CLOSED
    
    def reabrir(self) -> None:
        """Reabre un ticket cerrado o resuelto."""
        self.estado = TicketStatus.PENDING
        self.fecha_resolucion = None
    
    def actualizar_prioridad(self, prioridad: int) -> None:
        """
        Actualiza la prioridad del ticket.
        
        Args:
            prioridad: Nueva prioridad (1-5)
        """
        self.prioridad = max(1, min(5, prioridad))  # Asegurar que esté entre 1-5