# bot_siacasa/infrastructure/db/support_repository.py
import logging
import json
from typing import Dict, List, Optional
from datetime import datetime
import uuid

from bot_siacasa.domain.entities.ticket import Ticket, TicketStatus, EscalationReason
from bot_siacasa.domain.entities.usuario import Usuario
from bot_siacasa.domain.entities.conversacion import Conversacion
from bot_siacasa.domain.entities.mensaje import Mensaje  # Añadir esta importación

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
            
            self.db.execute("""
            CREATE TABLE IF NOT EXISTS ticket_user_mapping (
                ticket_id UUID PRIMARY KEY,
                user_id VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # Índice para búsquedas rápidas por usuario
            self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_ticket_user_user_id ON ticket_user_mapping(user_id);
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
            # 1. Intentar obtener desde metadatos del ticket
            if ticket.metadata and ticket.metadata.get('bank_code'):
                bank_code = ticket.metadata.get('bank_code')
            
            # 2. Si no, intentar obtener desde metadatos de la conversación
            elif hasattr(ticket.conversacion, 'metadata') and ticket.conversacion.metadata:
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
                metadata = EXCLUDED.metadata,
                bank_code = EXCLUDED.bank_code
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
            
            # Guardar la relación ticket-usuario en la tabla de mapeo
            try:
                query = """
                INSERT INTO ticket_user_mapping (ticket_id, user_id)
                VALUES (%s, %s)
                ON CONFLICT (ticket_id) DO NOTHING
                """
                
                self.db.execute(query, (ticket.id, ticket.usuario.id))
                logger.info(f"Relación ticket-usuario guardada: {ticket.id} - {ticket.usuario.id}")
                
                # Actualizar la caché local si existe
                if hasattr(self, 'ticket_users'):
                    self.ticket_users[ticket.id] = ticket.usuario.id
                    
            except Exception as e:
                logger.warning(f"Error al guardar relación ticket-usuario: {e}")
            
            logger.info(f"Ticket guardado: {ticket.id} para banco: {bank_code}")
            
        except Exception as e:
            logger.error(f"Error al guardar ticket {ticket.id}: {e}", exc_info=True)
            raise
    
    # Modified version of the _obtener_conversacion method in support_repository.py

    def _obtener_conversacion(self, conversacion_id: str) -> Optional[Conversacion]:
        """
        Obtiene una conversación por su ID.
        
        Args:
            conversacion_id: ID de la conversación
            
        Returns:
            Conversación o None si no existe
        """
        try:
            # Obtener información básica de la conversación
            query = """
            SELECT 
                id, user_id, start_time, end_time, message_count, metadata,
                COALESCE(last_activity_time, start_time) as last_activity_time
            FROM 
                chatbot_sessions
            WHERE 
                id = %s
            """
            
            conversacion_data = self.db.fetch_one(query, (conversacion_id,))
            
            if not conversacion_data:
                logger.warning(f"Conversación no encontrada: {conversacion_id}")
                return None
            
            # Obtener usuario
            usuario = self._obtener_usuario(conversacion_data['user_id'])
            
            if not usuario:
                logger.warning(f"Usuario no encontrado para conversación: {conversacion_id}")
                usuario_id = conversacion_data['user_id']
                # Crear un usuario básico en caso de error
                from bot_siacasa.domain.entities.usuario import Usuario
                usuario = Usuario(id=usuario_id)
            
            # Procesar metadata - verificar si ya es un dict
            metadata = conversacion_data['metadata']
            if metadata:
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except json.JSONDecodeError:
                        logger.warning(f"Error al decodificar JSON de metadata para conversación: {conversacion_id}")
                        metadata = {}
                # Si ya es un dict, no hacer nada
            else:
                metadata = {}
                
            # Crear objeto Conversacion
            from bot_siacasa.domain.entities.conversacion import Conversacion
            from bot_siacasa.domain.entities.mensaje import Mensaje
            
            conversacion = Conversacion(
                id=conversacion_id,
                usuario=usuario,
                fecha_inicio=conversacion_data['start_time'],
                fecha_fin=conversacion_data['end_time'],
                fecha_ultima_actividad=conversacion_data['last_activity_time'],
                metadata=metadata
            )
            
            # Verificar si la tabla chat_messages existe antes de consultarla
            try:
                # Intentar detectar si la tabla existe
                check_query = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'chat_messages'
                );
                """
                table_exists = self.db.fetch_one(check_query)
                
                if table_exists and table_exists.get('exists', False):
                    # Si la tabla existe, obtener mensajes
                    query = """
                    SELECT 
                        role, content, timestamp, metadata
                    FROM 
                        chat_messages
                    WHERE 
                        conversation_id = %s
                    ORDER BY 
                        timestamp ASC
                    """
                    
                    mensajes_data = self.db.fetch_all(query, (conversacion_id,))
                    
                    # Agregar mensajes al objeto Conversacion
                    for mensaje_data in mensajes_data:
                        # Procesar metadata del mensaje
                        msg_metadata = mensaje_data['metadata']
                        if msg_metadata and isinstance(msg_metadata, str):
                            try:
                                msg_metadata = json.loads(msg_metadata)
                            except:
                                msg_metadata = None
                        
                        mensaje = Mensaje(
                            role=mensaje_data['role'],
                            content=mensaje_data['content'],
                            timestamp=mensaje_data['timestamp'],
                            metadata=msg_metadata
                        )
                        conversacion.mensajes.append(mensaje)
                else:
                    # La tabla no existe, crear al menos mensajes básicos
                    logger.warning(f"Tabla chat_messages no encontrada, creando conversación básica")
                    # Agregar mensaje de sistema para que la conversación tenga contenido
                    mensaje_sistema = Mensaje(
                        role="system",
                        content="Soy SIACASA, tu asistente bancario virtual."
                    )
                    conversacion.mensajes.append(mensaje_sistema)
                    
                    # Agregar mensaje del usuario y del asistente como simulación
                    mensaje_usuario = Mensaje(
                        role="user",
                        content="Hola, necesito ayuda con mi cuenta."
                    )
                    conversacion.mensajes.append(mensaje_usuario)
                    
                    mensaje_asistente = Mensaje(
                        role="assistant", 
                        content="Hola, soy SIACASA, tu asistente bancario virtual. ¿En qué puedo ayudarte con tu cuenta?"
                    )
                    conversacion.mensajes.append(mensaje_asistente)
                    
            except Exception as e:
                # Si hay error al obtener mensajes, registrarlo pero continuar
                logger.warning(f"Error al obtener mensajes de conversación {conversacion_id}: {e}")
                # Agregar al menos un mensaje de sistema para que la conversación tenga contenido
                mensaje_sistema = Mensaje(
                    role="system",
                    content="Soy SIACASA, tu asistente bancario virtual."
                )
                conversacion.mensajes.append(mensaje_sistema)
            
            return conversacion
            
        except Exception as e:
            logger.error(f"Error al obtener conversación {conversacion_id}: {e}", exc_info=True)
            return None
        
    def obtener_usuario_por_ticket(self, ticket_id: str) -> Optional[str]:
        """
        Obtiene el ID del usuario asociado a un ticket.
        
        Args:
            ticket_id: ID del ticket
            
        Returns:
            ID del usuario o None si no existe
        """
        try:
            # Intentar obtener desde la tabla de tickets
            query = "SELECT user_id FROM support_tickets WHERE id = %s"
            result = self.db.fetch_one(query, (ticket_id,))
            
            if result and 'user_id' in result:
                return result['user_id']
            
            return None
        except Exception as e:
            logger.error(f"Error al obtener usuario por ticket: {e}", exc_info=True)
            return None
        
    def _obtener_usuario(self, usuario_id: str) -> Optional[Usuario]:
        """
        Obtiene un usuario por su ID.
        
        Args:
            usuario_id: ID del usuario
            
        Returns:
            Usuario o None si no existe
        """
        try:
            # Crear objeto Usuario básico
            # No consultamos la base de datos ya que no tenemos tabla de usuarios
            from bot_siacasa.domain.entities.usuario import Usuario
            
            usuario = Usuario(id=usuario_id)
            
            # Intentar obtener información adicional del usuario si está disponible
            # desde la tabla de sesiones de chatbot
            query = """
            SELECT 
                DISTINCT user_id, metadata
            FROM 
                chatbot_sessions
            WHERE 
                user_id = %s
            LIMIT 1
            """
            
            session_data = self.db.fetch_one(query, (usuario_id,))
            
            if session_data and session_data.get('metadata'):
                # Extraer datos posibles del usuario desde los metadatos de la sesión
                metadata = json.loads(session_data['metadata']) if isinstance(session_data['metadata'], str) else session_data['metadata']
                
                if metadata and isinstance(metadata, dict):
                    # Si hay datos de usuario en los metadatos, los utilizamos
                    if 'usuario' in metadata:
                        usuario_info = metadata['usuario']
                        if isinstance(usuario_info, dict):
                            if 'nombre' in usuario_info:
                                usuario.nombre = usuario_info['nombre']
                            if 'datos' in usuario_info:
                                usuario.datos = usuario_info['datos']
                            if 'preferencias' in usuario_info:
                                usuario.preferencias = usuario_info['preferencias']
            
            return usuario
            
        except Exception as e:
            logger.error(f"Error al obtener usuario {usuario_id}: {e}", exc_info=True)
            # En caso de error, devolver un usuario básico
            from bot_siacasa.domain.entities.usuario import Usuario
            return Usuario(id=usuario_id)
    
    # Modified version of the obtener_ticket method in support_repository.py

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
            
            # Procesar metadata - FIX: Verificar si metadata ya es un dict antes de usar json.loads
            metadata = ticket_data['metadata']
            if metadata:
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except json.JSONDecodeError:
                        logger.warning(f"Error al decodificar JSON de metadata para ticket: {ticket_id}")
                        metadata = {}
            else:
                metadata = {}
            
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
                metadata=metadata  # Using processed metadata
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
            # Logging para depuración
            logger.info(f"Agregando mensaje de agente: ticket_id={ticket_id}, agente={agente_nombre}, es_interno={es_interno}")
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