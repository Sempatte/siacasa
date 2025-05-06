# admin_panel/support/support_service.py
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union

from bot_siacasa.domain.entities.ticket import Ticket, TicketStatus, EscalationReason
from bot_siacasa.infrastructure.websocket.socket_server import get_websocket_server

logger = logging.getLogger(__name__)

class SupportService:
    """
    Servicio para gestionar tickets de soporte y escalaciones a humanos.
    """
    
    def __init__(self, support_repository):
        """
        Inicializa el servicio de soporte.
        
        Args:
            support_repository: Repositorio para tickets de soporte
        """
        self.repository = support_repository
    
    def get_pending_tickets(self, bank_code: Optional[str] = None) -> List[Ticket]:
        """
        Obtiene los tickets pendientes.
        
        Args:
            bank_code: Código del banco (opcional)
            
        Returns:
            Lista de tickets pendientes
        """
        try:
            # Obtener tickets pendientes
            pending_tickets = self.repository.obtener_tickets_por_estado(TicketStatus.PENDING, bank_code)
            
            logger.info(f"Obtenidos {len(pending_tickets)} tickets pendientes para banco {bank_code}")
            return pending_tickets
            
        except Exception as e:
            logger.error(f"Error al obtener tickets pendientes: {e}", exc_info=True)
            return []
    
    def get_assigned_tickets(self, agent_id: str) -> List[Ticket]:
        """
        Obtiene los tickets asignados a un agente.
        
        Args:
            agent_id: ID del agente
            
        Returns:
            Lista de tickets asignados
        """
        try:
            # Obtener tickets asignados al agente
            assigned_tickets = self.repository.obtener_tickets_por_agente(agent_id)
            
            logger.info(f"Obtenidos {len(assigned_tickets)} tickets asignados al agente {agent_id}")
            return assigned_tickets
            
        except Exception as e:
            logger.error(f"Error al obtener tickets asignados: {e}", exc_info=True)
            return []
    
    def get_ticket_details(self, ticket_id: str) -> Optional[Ticket]:
        """
        Obtiene los detalles de un ticket.
        
        Args:
            ticket_id: ID del ticket
            
        Returns:
            Ticket o None si no existe
        """
        try:
            # Obtener ticket
            ticket = self.repository.obtener_ticket(ticket_id)
            
            if not ticket:
                logger.warning(f"Ticket no encontrado: {ticket_id}")
            
            return ticket
            
        except Exception as e:
            logger.error(f"Error al obtener detalles del ticket {ticket_id}: {e}", exc_info=True)
            return None
    
    def get_ticket_bank(self, ticket_id: str) -> Optional[str]:
        """
        Obtiene el código del banco al que pertenece un ticket.
        
        Args:
            ticket_id: ID del ticket
            
        Returns:
            Código del banco o None si no se puede determinar
        """
        try:
            # Obtener banco del ticket
            query = "SELECT bank_code FROM support_tickets WHERE id = %s"
            result = self.repository.db.fetch_one(query, (ticket_id,))
            
            return result['bank_code'] if result else None
            
        except Exception as e:
            logger.error(f"Error al obtener banco del ticket {ticket_id}: {e}", exc_info=True)
            return None
    
    def get_ticket_messages(self, ticket_id: str) -> List[Dict]:
        """
        Obtiene los mensajes de un ticket.
        
        Args:
            ticket_id: ID del ticket
            
        Returns:
            Lista de mensajes
        """
        try:
            # Obtener mensajes de agente para este ticket
            query = """
            SELECT 
                id, agent_id as sender_id, agent_name as sender_name, 
                content, timestamp, is_internal,
                'agent' as sender_type
            FROM 
                agent_messages
            WHERE 
                ticket_id = %s
            ORDER BY 
                timestamp ASC
            """
            
            agent_messages = self.repository.db.fetch_all(query, (ticket_id,))
            
            # Convertir a formato común
            messages = []
            for msg in agent_messages:
                messages.append({
                    'id': msg['id'],
                    'sender_id': msg['sender_id'],
                    'sender_name': msg['sender_name'],
                    'content': msg['content'],
                    'timestamp': msg['timestamp'],
                    'is_internal': msg['is_internal'],
                    'sender_type': 'agent'
                })
            
            # Obtener mensajes del usuario desde la conversación
            ticket = self.repository.obtener_ticket(ticket_id)
            if ticket and hasattr(ticket.conversacion, 'mensajes'):
                for mensaje in ticket.conversacion.mensajes:
                    # Solo incluir mensajes del usuario
                    if mensaje.role == "user":
                        # Generar ID único para el mensaje
                        msg_id = f"user_{mensaje.timestamp.isoformat()}"
                        
                        messages.append({
                            'id': msg_id,
                            'sender_id': ticket.usuario.id,
                            'sender_name': ticket.usuario.nombre or "Usuario",
                            'content': mensaje.content,
                            'timestamp': mensaje.timestamp,
                            'is_internal': False,
                            'sender_type': 'user'
                        })
                    # Incluir mensajes del asistente que fueron enviados por un agente
                    elif mensaje.role == "assistant" and hasattr(mensaje, 'metadata') and mensaje.metadata:
                        if mensaje.metadata.get('from_agent', False):
                            # Usar ID proporcionado si existe
                            msg_id = mensaje.metadata.get('id', f"agent_{mensaje.timestamp.isoformat()}")
                            
                            messages.append({
                                'id': msg_id,
                                'sender_id': mensaje.metadata.get('agent_id', 'unknown'),
                                'sender_name': mensaje.metadata.get('agent_name', 'Agente'),
                                'content': mensaje.content,
                                'timestamp': mensaje.timestamp,
                                'is_internal': False,
                                'sender_type': 'agent'
                            })
            
            # Ordenar mensajes por timestamp
            messages.sort(key=lambda x: x['timestamp'])
            
            return messages
            
        except Exception as e:
            logger.error(f"Error al obtener mensajes del ticket {ticket_id}: {e}", exc_info=True)
            return []
    
    def get_conversation_history(self, ticket_id: str) -> List[Dict]:
        """
        Obtiene el historial completo de conversación para un ticket.
        
        Args:
            ticket_id: ID del ticket
            
        Returns:
            Lista de mensajes del historial
        """
        try:
            # Obtener ticket
            ticket = self.repository.obtener_ticket(ticket_id)
            if not ticket or not hasattr(ticket.conversacion, 'mensajes'):
                logger.warning(f"No se pudo obtener conversación para ticket: {ticket_id}")
                return []
            
            # Convertir mensajes de la conversación a formato para UI
            history = []
            for mensaje in ticket.conversacion.mensajes:
                # Determinar tipo de remitente
                sender_type = "user" if mensaje.role == "user" else "assistant"
                
                # Generar ID único para el mensaje
                msg_id = f"{sender_type}_{mensaje.timestamp.isoformat()}"
                
                # Determinar si el mensaje es de un agente humano
                is_from_agent = False
                agent_id = None
                agent_name = None
                
                if hasattr(mensaje, 'metadata') and mensaje.metadata:
                    is_from_agent = mensaje.metadata.get('from_agent', False)
                    agent_id = mensaje.metadata.get('agent_id')
                    agent_name = mensaje.metadata.get('agent_name')
                
                history.append({
                    'id': msg_id,
                    'content': mensaje.content,
                    'timestamp': mensaje.timestamp,
                    'role': mensaje.role,
                    'is_from_agent': is_from_agent,
                    'agent_id': agent_id,
                    'agent_name': agent_name
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Error al obtener historial de conversación del ticket {ticket_id}: {e}", exc_info=True)
            return []
    
    def get_user_info(self, user_id: str) -> Dict:
        """
        Obtiene información del usuario.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Diccionario con información del usuario
        """
        try:
            # Obtener información del usuario
            query = """
            SELECT 
                cs.user_id, 
                COUNT(DISTINCT cs.id) as total_sessions,
                MAX(cs.start_time) as last_activity,
                COALESCE(AVG(cs.message_count), 0) as avg_messages
            FROM 
                chatbot_sessions cs
            WHERE 
                cs.user_id = %s
            GROUP BY 
                cs.user_id
            """
            
            user_data = self.repository.db.fetch_one(query, (user_id,))
            
            if not user_data:
                return {
                    'user_id': user_id,
                    'total_sessions': 0,
                    'last_activity': None,
                    'avg_messages': 0,
                    'user_type': 'Desconocido'
                }
            
            # Determinar tipo de usuario basado en su actividad
            user_type = 'Nuevo'
            if user_data['total_sessions'] > 5:
                user_type = 'Recurrente'
            elif user_data['total_sessions'] > 10:
                user_type = 'Habitual'
            
            return {
                'user_id': user_id,
                'total_sessions': user_data['total_sessions'],
                'last_activity': user_data['last_activity'],
                'avg_messages': round(user_data['avg_messages'], 1),
                'user_type': user_type
            }
            
        except Exception as e:
            logger.error(f"Error al obtener información del usuario {user_id}: {e}", exc_info=True)
            return {
                'user_id': user_id,
                'total_sessions': 0,
                'last_activity': None,
                'avg_messages': 0,
                'user_type': 'Desconocido'
            }
    
    def assign_ticket(self, ticket_id: str, agent_id: str, agent_name: str) -> bool:
        """
        Asigna un ticket a un agente.
        
        Args:
            ticket_id: ID del ticket
            agent_id: ID del agente
            agent_name: Nombre del agente
            
        Returns:
            True si se asignó correctamente, False en caso contrario
        """
        try:
            # Obtener ticket
            ticket = self.repository.obtener_ticket(ticket_id)
            if not ticket:
                logger.warning(f"Ticket no encontrado: {ticket_id}")
                return False
            
            # Verificar que el ticket no esté ya asignado a otro agente
            if ticket.agente_id and ticket.agente_id != agent_id:
                logger.warning(f"El ticket {ticket_id} ya está asignado a otro agente")
                return False
            
            # Asignar ticket
            ticket.asignar_agente(agent_id, agent_name)
            
            # Guardar cambios
            self.repository.guardar_ticket(ticket)
            
            # Notificar al usuario
            self._notify_user_of_assignment(ticket, agent_name)
            
            logger.info(f"Ticket {ticket_id} asignado al agente {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error al asignar ticket {ticket_id} al agente {agent_id}: {e}", exc_info=True)
            return False
    
    def _notify_user_of_assignment(self, ticket: Ticket, agent_name: str) -> None:
        """
        Notifica al usuario que su ticket ha sido asignado a un agente.
        
        Args:
            ticket: Ticket asignado
            agent_name: Nombre del agente
        """
        try:
            # Crear mensaje para el usuario
            mensaje = f"Tu consulta ha sido asignada al agente {agent_name}. Pronto te responderá."
            
            # Agregar mensaje a la conversación (como mensaje del asistente)
            from bot_siacasa.domain.entities.mensaje import Mensaje
            mensaje_obj = Mensaje(
                role="assistant",
                content=mensaje
            )
            
            # Agregar a la conversación
            ticket.conversacion.agregar_mensaje(mensaje_obj)
            
            # Guardar cambios en el repositorio
            # NOTA: La conversación ya se guarda al guardar el ticket
            
        except Exception as e:
            logger.error(f"Error al notificar al usuario sobre asignación: {e}")
    
    def resolve_ticket(self, ticket_id: str, notes: Optional[str] = None) -> bool:
        """
        Marca un ticket como resuelto.
        
        Args:
            ticket_id: ID del ticket
            notes: Notas sobre la resolución
            
        Returns:
            True si se resolvió correctamente, False en caso contrario
        """
        try:
            # Obtener ticket
            ticket = self.repository.obtener_ticket(ticket_id)
            if not ticket:
                logger.warning(f"Ticket no encontrado: {ticket_id}")
                return False
            
            # Resolver ticket
            ticket.resolver(notes)
            
            # Guardar cambios
            self.repository.guardar_ticket(ticket)
            
            # Notificar al usuario
            self._notify_user_of_resolution(ticket)
            
            logger.info(f"Ticket {ticket_id} marcado como resuelto")
            return True
            
        except Exception as e:
            logger.error(f"Error al resolver ticket {ticket_id}: {e}", exc_info=True)
            return False
    
    def _notify_user_of_resolution(self, ticket: Ticket) -> None:
        """
        Notifica al usuario que su ticket ha sido resuelto.
        
        Args:
            ticket: Ticket resuelto
        """
        try:
            # Crear mensaje para el usuario
            mensaje = "Tu consulta ha sido marcada como resuelta. Si necesitas más ayuda, no dudes en decirlo."
            
            # Agregar mensaje a la conversación (como mensaje del asistente)
            from bot_siacasa.domain.entities.mensaje import Mensaje
            mensaje_obj = Mensaje(
                role="assistant",
                content=mensaje
            )
            
            # Agregar a la conversación
            ticket.conversacion.agregar_mensaje(mensaje_obj)
            
            # Guardar cambios en el repositorio
            # NOTA: La conversación ya se guarda al guardar el ticket
            
        except Exception as e:
            logger.error(f"Error al notificar al usuario sobre resolución: {e}")
    
    def close_ticket(self, ticket_id: str) -> bool:
        """
        Cierra un ticket definitivamente.
        
        Args:
            ticket_id: ID del ticket
            
        Returns:
            True si se cerró correctamente, False en caso contrario
        """
        try:
            # Obtener ticket
            ticket = self.repository.obtener_ticket(ticket_id)
            if not ticket:
                logger.warning(f"Ticket no encontrado: {ticket_id}")
                return False
            
            # Cerrar ticket
            ticket.cerrar()
            
            # Guardar cambios
            self.repository.guardar_ticket(ticket)
            
            logger.info(f"Ticket {ticket_id} cerrado")
            return True
            
        except Exception as e:
            logger.error(f"Error al cerrar ticket {ticket_id}: {e}", exc_info=True)
            return False
    
    def unassign_ticket(self, ticket_id: str) -> bool:
        """
        Desasigna un ticket.
        
        Args:
            ticket_id: ID del ticket
            
        Returns:
            True si se desasignó correctamente, False en caso contrario
        """
        try:
            # Obtener ticket
            ticket = self.repository.obtener_ticket(ticket_id)
            if not ticket:
                logger.warning(f"Ticket no encontrado: {ticket_id}")
                return False
            
            # Desasignar ticket
            ticket.agente_id = None
            ticket.agente_nombre = None
            ticket.fecha_asignacion = None
            ticket.estado = TicketStatus.PENDING
            
            # Guardar cambios
            self.repository.guardar_ticket(ticket)
            
            # Notificar al usuario
            self._notify_user_of_unassignment(ticket)
            
            logger.info(f"Ticket {ticket_id} desasignado")
            return True
            
        except Exception as e:
            logger.error(f"Error al desasignar ticket {ticket_id}: {e}", exc_info=True)
            return False
    
    def _notify_user_of_unassignment(self, ticket: Ticket) -> None:
        """
        Notifica al usuario que su ticket ha sido desasignado.
        
        Args:
            ticket: Ticket desasignado
        """
        try:
            # Crear mensaje para el usuario
            mensaje = "Tu consulta ha sido reasignada. Un nuevo agente te atenderá pronto."
            
            # Agregar mensaje a la conversación (como mensaje del asistente)
            from bot_siacasa.domain.entities.mensaje import Mensaje
            mensaje_obj = Mensaje(
                role="assistant",
                content=mensaje
            )
            
            # Agregar a la conversación
            ticket.conversacion.agregar_mensaje(mensaje_obj)
            
            # Guardar cambios en el repositorio
            # NOTA: La conversación ya se guarda al guardar el ticket
            
        except Exception as e:
            logger.error(f"Error al notificar al usuario sobre desasignación: {e}")
    
    def set_ticket_status(self, ticket_id: str, status: TicketStatus) -> bool:
        """
        Cambia el estado de un ticket.
        
        Args:
            ticket_id: ID del ticket
            status: Nuevo estado
            
        Returns:
            True si se cambió correctamente, False en caso contrario
        """
        try:
            # Obtener ticket
            ticket = self.repository.obtener_ticket(ticket_id)
            if not ticket:
                logger.warning(f"Ticket no encontrado: {ticket_id}")
                return False
            
            # Cambiar estado
            ticket.estado = status
            
            # Guardar cambios
            self.repository.guardar_ticket(ticket)
            
            logger.info(f"Estado del ticket {ticket_id} cambiado a {status.value}")
            return True
            
        except Exception as e:
            logger.error(f"Error al cambiar estado del ticket {ticket_id}: {e}", exc_info=True)
            return False
    
    def send_message(self, ticket_id: str, agent_id: str, agent_name: str, content: str, is_internal: bool = False) -> bool:
        """
        Envía un mensaje en un ticket.
        
        Args:
            ticket_id: ID del ticket
            agent_id: ID del agente
            agent_name: Nombre del agente
            content: Contenido del mensaje
            is_internal: Indica si el mensaje es interno (solo visible para agentes)
            
        Returns:
            True si se envió correctamente, False en caso contrario
        """
        try:
            # Guardar mensaje en el repositorio
            mensaje_id = self.repository.agregar_mensaje_agente(
                ticket_id, 
                agent_id, 
                agent_name, 
                content, 
                is_internal
            )
            
            if not mensaje_id:
                logger.warning(f"Error al guardar mensaje en ticket {ticket_id}")
                return False
            
            # Enviar mensaje a través del WebSocket
            websocket_server = get_websocket_server()
            if websocket_server:
                # Añadir log para depuración
                logger.info(f"Enviando mensaje por WebSocket. Servidor: {websocket_server}")
                
                # Crear un bucle de eventos para ejecutar código asyncio
                import asyncio
                
                async def send_ws_message():
                    try:
                        await websocket_server.broadcast_message(
                            ticket_id,
                            content,
                            agent_id,
                            agent_name,
                            'agent',
                            is_internal
                        )
                        logger.info(f"Mensaje enviado por WebSocket correctamente a ticket {ticket_id}")
                    except Exception as e:
                        logger.error(f"Error al enviar mensaje por WebSocket: {e}", exc_info=True)
                
                # Ejecutar función async con mejor manejo de errores
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(send_ws_message())
                except Exception as e:
                    logger.error(f"Error en el loop de asyncio: {e}", exc_info=True)
                finally:
                    loop.close()
            else:
                logger.warning("No se encontró servidor WebSocket para enviar mensaje")
        
            logger.info(f"Mensaje enviado en ticket {ticket_id}" + (" (interno)" if is_internal else ""))
            return True
            
        except Exception as e:
            logger.error(f"Error al enviar mensaje en ticket {ticket_id}: {e}", exc_info=True)
            return False
    
    def send_typing_notification(self, ticket_id: str, agent_id: str, agent_name: str, is_typing: bool = True) -> bool:
        """
        Envía una notificación de escritura.
        
        Args:
            ticket_id: ID del ticket
            agent_id: ID del agente
            agent_name: Nombre del agente
            is_typing: Indica si el agente está escribiendo
            
        Returns:
            True si se envió correctamente, False en caso contrario
        """
        try:
            # Enviar notificación a través del WebSocket
            websocket_server = get_websocket_server()
            if websocket_server:
                # Crear un bucle de eventos para ejecutar código asyncio
                import asyncio
                
                async def send_ws_typing():
                    await websocket_server.broadcast_typing(
                        ticket_id,
                        agent_id,
                        'agent',
                        is_typing
                    )
                
                # Ejecutar función async
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(send_ws_typing())
                finally:
                    loop.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error al enviar notificación de escritura en ticket {ticket_id}: {e}", exc_info=True)
            return False
    
    def get_support_stats(self, bank_code: Optional[str] = None) -> Dict:
        """
        Obtiene estadísticas de soporte.
        
        Args:
            bank_code: Código del banco (opcional)
            
        Returns:
            Diccionario con estadísticas
        """
        try:
            # Preparar condición de banco
            bank_condition = f"AND bank_code = '{bank_code}'" if bank_code else ""
            
            # Total de tickets
            query = f"""
            SELECT COUNT(*) as count
            FROM support_tickets
            WHERE 1=1 {bank_condition}
            """
            total_result = self.repository.db.fetch_one(query)
            total_tickets = total_result['count'] if total_result else 0
            
            # Tickets por estado
            query = f"""
            SELECT status, COUNT(*) as count
            FROM support_tickets
            WHERE 1=1 {bank_condition}
            GROUP BY status
            """
            status_results = self.repository.db.fetch_all(query)
            
            status_counts = {}
            for row in status_results:
                status_counts[row['status']] = row['count']
            
            # Tiempo promedio de resolución (en minutos)
            query = f"""
            SELECT AVG(EXTRACT(EPOCH FROM (resolution_date - creation_date))) / 60 as avg_resolution_time
            FROM support_tickets
            WHERE resolution_date IS NOT NULL {bank_condition}
            """
            resolution_result = self.repository.db.fetch_one(query)
            avg_resolution_time = round(resolution_result['avg_resolution_time'], 2) if resolution_result and resolution_result['avg_resolution_time'] else 0
            
            # Tickets creados hoy
            query = f"""
            SELECT COUNT(*) as count
            FROM support_tickets
            WHERE DATE(creation_date) = CURRENT_DATE {bank_condition}
            """
            today_result = self.repository.db.fetch_one(query)
            tickets_today = today_result['count'] if today_result else 0
            
            # Tickets resueltos hoy
            query = f"""
            SELECT COUNT(*) as count
            FROM support_tickets
            WHERE DATE(resolution_date) = CURRENT_DATE {bank_condition}
            """
            resolved_today_result = self.repository.db.fetch_one(query)
            resolved_today = resolved_today_result['count'] if resolved_today_result else 0
            
            # Compilar estadísticas
            stats = {
                'total_tickets': total_tickets,
                'pending_tickets': status_counts.get('pending', 0),
                'assigned_tickets': status_counts.get('assigned', 0),
                'active_tickets': status_counts.get('active', 0),
                'resolved_tickets': status_counts.get('resolved', 0),
                'closed_tickets': status_counts.get('closed', 0),
                'avg_resolution_time': avg_resolution_time,
                'tickets_today': tickets_today,
                'resolved_today': resolved_today
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error al obtener estadísticas de soporte: {e}", exc_info=True)
            return {
                'total_tickets': 0,
                'pending_tickets': 0,
                'assigned_tickets': 0,
                'active_tickets': 0,
                'resolved_tickets': 0,
                'closed_tickets': 0,
                'avg_resolution_time': 0,
                'tickets_today': 0,
                'resolved_today': 0
            }
    
    def get_recent_tickets(self, bank_code: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """
        Obtiene tickets recientes.
        
        Args:
            bank_code: Código del banco (opcional)
            limit: Límite de tickets a obtener
            
        Returns:
            Lista de tickets recientes
        """
        try:
            # Preparar condición de banco
            bank_condition = f"AND bank_code = '{bank_code}'" if bank_code else ""
            
            # Consultar tickets recientes
            query = f"""
            SELECT 
                id, user_id, status, escalation_reason, 
                creation_date, assignment_date, resolution_date,
                agent_id, agent_name, priority
            FROM 
                support_tickets
            WHERE 
                1=1 {bank_condition}
            ORDER BY 
                creation_date DESC
            LIMIT {limit}
            """
            
            recent_tickets = self.repository.db.fetch_all(query)
            
            # Convertir a formato amigable
            result = []
            for ticket in recent_tickets:
                # Formatear fechas
                creation_date = ticket['creation_date'].strftime('%d/%m/%Y %H:%M') if ticket['creation_date'] else None
                assignment_date = ticket['assignment_date'].strftime('%d/%m/%Y %H:%M') if ticket['assignment_date'] else None
                resolution_date = ticket['resolution_date'].strftime('%d/%m/%Y %H:%M') if ticket['resolution_date'] else None
                
                result.append({
                    'id': ticket['id'],
                    'user_id': ticket['user_id'],
                    'status': ticket['status'],
                    'escalation_reason': ticket['escalation_reason'],
                    'creation_date': creation_date,
                    'assignment_date': assignment_date,
                    'resolution_date': resolution_date,
                    'agent_id': ticket['agent_id'],
                    'agent_name': ticket['agent_name'],
                    'priority': ticket['priority']
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error al obtener tickets recientes: {e}", exc_info=True)
            return []
    
    def get_chart_data(self, bank_code: Optional[str] = None) -> Dict:
        """
        Obtiene datos para gráficos.
        
        Args:
            bank_code: Código del banco (opcional)
            
        Returns:
            Diccionario con datos para gráficos
        """
        try:
            # Preparar condición de banco
            bank_condition = f"AND bank_code = '{bank_code}'" if bank_code else ""
            
            # Tickets por día (últimos 7 días)
            query = f"""
            SELECT 
                DATE(creation_date) as date,
                COUNT(*) as count
            FROM 
                support_tickets
            WHERE 
                creation_date >= CURRENT_DATE - INTERVAL '7 days' {bank_condition}
            GROUP BY 
                DATE(creation_date)
            ORDER BY 
                date ASC
            """
            tickets_by_day = self.repository.db.fetch_all(query)
            
            # Convertir a formato para gráfico
            dates = []
            counts = []
            for row in tickets_by_day:
                dates.append(row['date'].strftime('%d/%m'))
                counts.append(row['count'])
            
            # Tickets por razón de escalación
            query = f"""
            SELECT 
                escalation_reason,
                COUNT(*) as count
            FROM 
                support_tickets
            WHERE 
                1=1 {bank_condition}
            GROUP BY 
                escalation_reason
            ORDER BY 
                count DESC
            """
            tickets_by_reason = self.repository.db.fetch_all(query)
            
            # Convertir a formato para gráfico
            reasons = []
            reason_counts = []
            for row in tickets_by_reason:
                reasons.append(row['escalation_reason'])
                reason_counts.append(row['count'])
            
            # Tiempo promedio de resolución por día
            query = f"""
            SELECT 
                DATE(resolution_date) as date,
                AVG(EXTRACT(EPOCH FROM (resolution_date - creation_date))) / 60 as avg_time
            FROM 
                support_tickets
            WHERE 
                resolution_date IS NOT NULL 
                AND resolution_date >= CURRENT_DATE - INTERVAL '7 days' {bank_condition}
            GROUP BY 
                DATE(resolution_date)
            ORDER BY 
                date ASC
            """
            resolution_times = self.repository.db.fetch_all(query)
            
            # Convertir a formato para gráfico
            resolution_dates = []
            avg_times = []
            for row in resolution_times:
                resolution_dates.append(row['date'].strftime('%d/%m'))
                avg_times.append(round(row['avg_time'], 2))
            
            # Compilar datos para gráficos
            chart_data = {
                'tickets_by_day': {
                    'labels': dates,
                    'datasets': [{
                        'label': 'Tickets',
                        'data': counts,
                        'backgroundColor': 'rgba(0, 123, 255, 0.5)',
                        'borderColor': 'rgba(0, 123, 255, 1)',
                        'borderWidth': 1
                    }]
                },
                'tickets_by_reason': {
                    'labels': reasons,
                    'datasets': [{
                        'label': 'Tickets',
                        'data': reason_counts,
                        'backgroundColor': [
                            'rgba(255, 99, 132, 0.7)',
                            'rgba(54, 162, 235, 0.7)',
                            'rgba(255, 206, 86, 0.7)',
                            'rgba(75, 192, 192, 0.7)'
                        ],
                        'borderColor': [
                            'rgba(255, 99, 132, 1)',
                            'rgba(54, 162, 235, 1)',
                            'rgba(255, 206, 86, 1)',
                            'rgba(75, 192, 192, 1)'
                        ],
                        'borderWidth': 1
                    }]
                },
                'resolution_times': {
                    'labels': resolution_dates,
                    'datasets': [{
                        'label': 'Tiempo promedio (minutos)',
                        'data': avg_times,
                        'backgroundColor': 'rgba(40, 167, 69, 0.5)',
                        'borderColor': 'rgba(40, 167, 69, 1)',
                        'borderWidth': 1
                    }]
                }
            }
            
            return chart_data
            
        except Exception as e:
            logger.error(f"Error al obtener datos para gráficos: {e}", exc_info=True)
            return {
                'tickets_by_day': {'labels': [], 'datasets': [{'data': []}]},
                'tickets_by_reason': {'labels': [], 'datasets': [{'data': []}]},
                'resolution_times': {'labels': [], 'datasets': [{'data': []}]}
            }