# bot_siacasa/infrastructure/db/support_repository.py
import logging
import json
from typing import Dict, List, Optional
from datetime import datetime

from bot_siacasa.domain.entities.ticket import Ticket, TicketStatus, EscalationReason
from bot_siacasa.domain.entities.usuario import Usuario
from bot_siacasa.domain.entities.conversacion import Conversacion

logger = logging.getLogger(__name__)

class SupportRepository:
    """
    Repositorio para gestionar tickets de soporte en la base de datos.
    """
    
    def __init__(self, db_connector):
        """
        Inicializa el repositorio con el conector de base de datos.
        
        Args:
            db_connector: Conector a la base de datos
        """
        self.db = db_connector
        self._initialize_tables()
    
    def _initialize_tables(self) -> None:
        """
        Inicializa las tablas necesarias para el repositorio de soporte.
        """
        try:
            # Tabla de tickets
            self.db.execute("""
            CREATE TABLE IF NOT EXISTS support_tickets (
                id UUID PRIMARY KEY,
                conversation_id UUID NOT NULL,
                user_id VARCHAR(100) NOT NULL,
                status VARCHAR(20) NOT NULL,
                escalation_reason VARCHAR(50) NOT NULL,
                creation_date TIMESTAMP NOT NULL,
                assignment_date TIMESTAMP,
                resolution_date TIMESTAMP,
                agent_id UUID,
                agent_name VARCHAR(100),
                notes TEXT,
                priority INTEGER NOT NULL,
                metadata JSONB,
                bank_code VARCHAR(10) REFERENCES banks(code),
                FOREIGN KEY (conversation_id) REFERENCES chatbot_sessions(id)
            )
            """)
            
            # Índices para búsqueda eficiente
            self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_tickets_status ON support_tickets(status);
            """)
            
            self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_tickets_user_id ON support_tickets(user_id);
            """)
            
            self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_tickets_agent_id ON support_tickets(agent_id);
            """)
            
            self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_tickets_bank_code ON support_tickets(bank_code);
            """)
            
            # Tabla para mensajes de agentes (mensajes que no forman parte de la conversación principal)
            self.db.execute("""
            CREATE TABLE IF NOT EXISTS agent_messages (
                id UUID PRIMARY KEY,
                ticket_id UUID NOT NULL,
                agent_id UUID NOT NULL,
                agent_name VARCHAR(100) NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                is_internal BOOLEAN NOT NULL DEFAULT FALSE,
                FOREIGN KEY (ticket_id) REFERENCES support_tickets(id)
            )
            """)
            
            logger.info("Tablas de soporte inicializadas correctamente")
        except Exception as e:
            logger.error(f"Error al inicializar tablas de soporte: {e}", exc_info=True)
            raise
    
    def guardar_ticket(self, ticket: Ticket) -> None:
        """
        Guarda un ticket en la base de datos.
        
        Args:
            ticket: Ticket a guardar
        """
        try:
            # Obtener el código del banco desde la conversación
            bank_code = None
            if hasattr(ticket.conversacion, 'metadata') and ticket.conversacion.metadata:
                bank_code = ticket.conversacion.metadata.get('bank_code')
            
            # Convertir enums a strings
            status = ticket.estado.value
            reason = ticket.razon_escalacion.value
            
            # Convertir metadatos a JSON
            metadata_json = json.dumps(ticket.metadata) if ticket.metadata else None
            
            # Insertar ticket en la base de datos
            query = """
            INSERT INTO support_tickets (
                id, conversation_id, user_id, status, escalation_reason,
                creation_date, assignment_date, resolution_date,
                agent_id, agent_name, notes, priority, metadata, bank_code
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (id) DO UPDATE SET
                status = EXCLUDED.status,
                assignment_date = EXCLUDED.assignment_date,
                resolution_date = EXCLUDED.resolution_date,
                agent_id = EXCLUDED.agent_id,
                agent_name = EXCLUDED.agent_name,
                notes = EXCLUDED.notes,
                priority = EXCLUDED.priority,
                metadata = EXCLUDED.metadata
            """
            
            self.db.execute(
                query,
                (
                    ticket.id,
                    ticket.conversacion.id,
                    ticket.usuario.id,
                    status,
                    reason,
                    ticket.fecha_creacion,
                    ticket.fecha_asignacion,
                    ticket.fecha_resolucion,
                    ticket.agente_id,
                    ticket.agente_nombre,
                    ticket.notas,
                    ticket.prioridad,
                    metadata_json,
                    bank_code
                )
            )
            
            logger.info(f"Ticket guardado: {ticket.id}")
            
        except Exception as e:
            logger.error(f"Error al guardar ticket {ticket.id}: {e}", exc_info=True)
            raise
    
    def obtener_ticket(self, ticket_id: str) -> Optional[Ticket]:
        """
        Obtiene un ticket por su ID.
        
        Args:
            ticket_id: ID del ticket
            
        Returns:
            Ticket o None si no existe
        """
        try:
            query = """
            SELECT 
                t.id, t.conversation_id, t.user_id, t.status, t.escalation_reason,
                t.creation_date, t.assignment_date, t.resolution_date,
                t.agent_id, t.agent_name, t.notes, t.priority, t.metadata
            FROM 
                support_tickets t
            WHERE 
                t.id = %s
            """
            
            ticket_data = self.db.fetch_one(query, (ticket_id,))
            
            if not ticket_data:
                logger.warning(f"Ticket no encontrado: {ticket_id}")
                return None
            
            # Obtener conversación
            conversacion = self._obtener_conversacion(ticket_data['conversation_id'])
            
            if not conversacion:
                logger.warning(f"Conversación no encontrada para ticket: {ticket_id}")
                return None
            
            # Obtener usuario
            usuario = self._obtener_usuario(ticket_data['user_id'])
            
            if not usuario:
                logger.warning(f"Usuario no encontrado para ticket: {ticket_id}")
                return None
            
            # Reconstruir el ticket
            ticket = Ticket(
                id=ticket_data['id'],
                conversacion=conversacion,
                usuario=usuario,
                estado=TicketStatus(ticket_data['status']),
                razon_escalacion=EscalationReason(ticket_data['escalation_reason']),
                fecha_creacion=ticket_data['creation_date'],
                fecha_asignacion=ticket_data['assignment_date'],
                fecha_resolucion=ticket_data['resolution_date'],
                agente_id=ticket_data['agent_id'],
                agente_nombre=ticket_data['agent_name'],
                notas=ticket_data['notes'],
                prioridad=ticket_data['priority'],
                metadata=json.loads(ticket_data['metadata']) if ticket_data['metadata'] else {}
            )
            
            return ticket
            
        except Exception as e:
            logger.error(f"Error al obtener ticket {ticket_id}: {e}", exc_info=True)
            return None
    
    def obtener_tickets_por_estado(self, estado: TicketStatus, bank_code: Optional[str] = None) -> List[Ticket]:
        """
        Obtiene tickets por estado.
        
        Args:
            estado: Estado de los tickets a buscar
            bank_code: Código del banco (opcional)
            
        Returns:
            Lista de tickets en el estado especificado
        """
        try:
            status = estado.value
            
            if bank_code:
                query = """
                SELECT id FROM support_tickets 
                WHERE status = %s AND bank_code = %s
                ORDER BY priority DESC, creation_date ASC
                """
                ticket_ids = self.db.fetch_all(query, (status, bank_code))
            else:
                query = """
                SELECT id FROM support_tickets 
                WHERE status = %s
                ORDER BY priority DESC, creation_date ASC
                """
                ticket_ids = self.db.fetch_all(query, (status,))
            
            # Obtener tickets completos
            tickets = []
            for row in ticket_ids:
                ticket = self.obtener_ticket(row['id'])
                if ticket:
                    tickets.append(ticket)
            
            return tickets
            
        except Exception as e:
            logger.error(f"Error al obtener tickets por estado {estado.value}: {e}", exc_info=True)
            return []
    
    def obtener_tickets_por_agente(self, agente_id: str) -> List[Ticket]:
        """
        Obtiene tickets asignados a un agente.
        
        Args:
            agente_id: ID del agente
            
        Returns:
            Lista de tickets asignados al agente
        """
        try:
            query = """
            SELECT id FROM support_tickets 
            WHERE agent_id = %s AND status IN ('assigned', 'active')
            ORDER BY priority DESC, creation_date ASC
            """
            
            ticket_ids = self.db.fetch_all(query, (agente_id,))
            
            # Obtener tickets completos
            tickets = []
            for row in ticket_ids:
                ticket = self.obtener_ticket(row['id'])
                if ticket:
                    tickets.append(ticket)
            
            return tickets
            
        except Exception as e:
            logger.error(f"Error al obtener tickets por agente {agente_id}: {e}", exc_info=True)
            return []
    
    def obtener_tickets_por_usuario(self, usuario_id: str) -> List[Ticket]:
        """
        Obtiene tickets creados por un usuario.
        
        Args:
            usuario_id: ID del usuario
            
        Returns:
            Lista de tickets del usuario
        """
        try:
            query = """
            SELECT id FROM support_tickets 
            WHERE user_id = %s
            ORDER BY creation_date DESC
            """
            
            ticket_ids = self.db.fetch_all(query, (usuario_id,))
            
            # Obtener tickets completos
            tickets = []
            for row in ticket_ids:
                ticket = self.obtener_ticket(row['id'])
                if ticket:
                    tickets.append(ticket)
            
            return tickets
            
        except Exception as e:
            logger.error(f"Error al obtener tickets por usuario {usuario_id}: {e}", exc_info=True)
            return []
    
    def agregar_mensaje_agente(self, ticket_id: str, agente_id: str, agente_nombre: str, 
                              contenido: str, es_interno: bool = False) -> Optional[str]:
        """
        Agrega un mensaje de agente al ticket.
        
        Args:
            ticket_id: ID del ticket
            agente_id: ID del agente
            agente_nombre: Nombre del agente
            contenido: Contenido del mensaje
            es_interno: Indica si el mensaje es interno (solo visible para agentes)
            
        Returns:
            ID del mensaje o None si hay error
        """
        try:
            mensaje_id = str(uuid.uuid4())
            
            query = """
            INSERT INTO agent_messages (
                id, ticket_id, agent_id, agent_name, content, timestamp, is_internal
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s
            )
            """
            
            self.db.execute(
                query,
                (
                    mensaje_id,
                    ticket_id,
                    agente_id,
                    agente_nombre,
                    contenido,
                    datetime.now(),
                    es_interno
                )
            )
            
            # Si no es un mensaje interno, también añadir a la conversación
            if not es_interno:
                ticket = self.obtener_ticket(ticket_id)
                if ticket and ticket.conversacion:
                    # Crear mensaje del asistente
                    mensaje = Mensaje(
                        role="assistant",
                        content=contenido,
                        metadata={"from_agent": True, "agent_id": agente_id, "agent_name": agente_nombre}
                    )
                    
                    # Agregar a la conversación
                    ticket.conversacion.agregar_mensaje(mensaje)
                    
                    # Actualizar la conversación en la base de datos
                    from bot_siacasa.application.interfaces.repository_interface import IRepository
                    if isinstance(self, IRepository):
                        self.guardar_conversacion(ticket.conversacion)
            
            return mensaje_id
            
        except Exception as e:
            logger.error(f"Error al agregar mensaje de agente al ticket {ticket_id}: {e}", exc_info=True)
            return None