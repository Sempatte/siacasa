# admin_panel/support/support_controller.py
import logging
import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify

from admin_panel.auth.auth_middleware import login_required
from admin_panel.support.support_service import SupportService
from bot_siacasa.infrastructure.db.neondb_connector import NeonDBConnector
from bot_siacasa.infrastructure.db.support_repository import SupportRepository
from bot_siacasa.domain.entities.ticket import TicketStatus

logger = logging.getLogger(__name__)

# Crear blueprint para soporte
support_blueprint = Blueprint('support', __name__)

# Inicializar servicios
db_connector = NeonDBConnector()
support_repository = SupportRepository(db_connector)
support_service = SupportService(support_repository)

@support_blueprint.route('/')
@login_required
def index():
    """
    Muestra la página principal del panel de soporte.
    """
    bank_code = session.get('bank_code')
    bank_name = session.get('bank_name')
    user_name = session.get('user_name')
    
    # Obtener tickets pendientes
    pending_tickets = support_service.get_pending_tickets(bank_code)
    
    # Obtener tickets asignados al agente actual
    agent_id = session.get('user_id')
    assigned_tickets = support_service.get_assigned_tickets(agent_id)
    
    # Obtener estadísticas
    stats = support_service.get_support_stats(bank_code)
    
    return render_template(
        'support_dashboard.html',
        bank_name=bank_name,
        user_name=user_name,
        pending_tickets=pending_tickets,
        assigned_tickets=assigned_tickets,
        stats=stats
    )

@support_blueprint.route('/tickets/<ticket_id>')
@login_required
def ticket_details(ticket_id):
    """
    Muestra los detalles de un ticket.
    """
    bank_code = session.get('bank_code')
    bank_name = session.get('bank_name')
    user_name = session.get('user_name')
    agent_id = session.get('user_id')
    
    # Obtener ticket
    ticket = support_service.get_ticket_details(ticket_id)
    
    if not ticket:
        flash('Ticket no encontrado.', 'danger')
        return redirect(url_for('support.index'))
    
    # Verificar que el ticket pertenezca al banco actual
    ticket_bank = support_service.get_ticket_bank(ticket_id)
    if ticket_bank and ticket_bank != bank_code:
        flash('No tienes permisos para ver este ticket.', 'danger')
        return redirect(url_for('support.index'))
    
    # Obtener historial de mensajes
    messages = support_service.get_ticket_messages(ticket_id)
    
    # Obtener información del WebSocket
    websocket_info = {
        'host': request.host.split(':')[0],  # Obtener solo el hostname sin puerto
        'port': 8765,  # Puerto del WebSocket (debe coincidir con el del servidor)
        'agent_id': agent_id,
        'agent_name': user_name,
        'ticket_id': ticket_id
    }
    
    return render_template(
        'ticket_details.html',
        bank_name=bank_name,
        user_name=user_name,
        ticket=ticket,
        messages=messages,
        websocket_info=websocket_info
    )

@support_blueprint.route('/tickets/<ticket_id>/live-chat')
@login_required
def live_chat(ticket_id):
    """
    Muestra la interfaz de chat en vivo para un ticket.
    """
    bank_code = session.get('bank_code')
    bank_name = session.get('bank_name')
    user_name = session.get('user_name')
    agent_id = session.get('user_id')
    
    # Obtener ticket
    ticket = support_service.get_ticket_details(ticket_id)
    
    if not ticket:
        flash('Ticket no encontrado.', 'danger')
        return redirect(url_for('support.index'))
    
    # Verificar que el ticket pertenezca al banco actual
    ticket_bank = support_service.get_ticket_bank(ticket_id)
    if ticket_bank and ticket_bank != bank_code:
        flash('No tienes permisos para ver este ticket.', 'danger')
        return redirect(url_for('support.index'))
    
    # Verificar que el ticket esté asignado al agente actual
    if ticket.agente_id and ticket.agente_id != agent_id:
        # Si el ticket está asignado a otro agente, mostrar error
        flash('Este ticket está asignado a otro agente.', 'danger')
        return redirect(url_for('support.index'))
    
    # Si el ticket no está asignado, asignarlo al agente actual
    if not ticket.agente_id:
        success = support_service.assign_ticket(ticket_id, agent_id, user_name)
        if not success:
            flash('Error al asignar el ticket.', 'danger')
            return redirect(url_for('support.index'))
    
    # Cambiar estado del ticket a activo
    support_service.set_ticket_status(ticket_id, TicketStatus.ACTIVE)
    
    # Obtener historial de mensajes completo
    messages = support_service.get_ticket_messages(ticket_id)
    conversation_history = support_service.get_conversation_history(ticket_id)
    
    # Obtener información del WebSocket
    websocket_info = {
        'host': request.host.split(':')[0],  # Obtener solo el hostname sin puerto
        'port': 8765,  # Puerto del WebSocket (debe coincidir con el del servidor)
        'agent_id': agent_id,
        'agent_name': user_name,
        'ticket_id': ticket_id
    }
    
    # Obtener información del usuario
    user_info = support_service.get_user_info(ticket.usuario.id)
    
    return render_template(
        'live_chat.html',
        bank_name=bank_name,
        user_name=user_name,
        ticket=ticket,
        messages=messages,
        conversation_history=conversation_history,
        websocket_info=websocket_info,
        user_info=user_info
    )

@support_blueprint.route('/tickets/<ticket_id>/assign', methods=['POST'])
@login_required
def assign_ticket(ticket_id):
    """
    Asigna un ticket al agente actual.
    """
    agent_id = session.get('user_id')
    agent_name = session.get('user_name')
    
    # Asignar ticket
    success = support_service.assign_ticket(ticket_id, agent_id, agent_name)
    
    if success:
        flash('Ticket asignado correctamente.', 'success')
    else:
        flash('Error al asignar el ticket.', 'danger')
    
    # Redireccionar según origen
    referer = request.form.get('referer')
    if referer == 'details':
        return redirect(url_for('support.ticket_details', ticket_id=ticket_id))
    else:
        return redirect(url_for('support.index'))

@support_blueprint.route('/tickets/<ticket_id>/resolve', methods=['POST'])
@login_required
def resolve_ticket(ticket_id):
    """
    Marca un ticket como resuelto.
    """
    agent_id = session.get('user_id')
    resolution_notes = request.form.get('resolution_notes', '')
    
    # Verificar que el ticket esté asignado al agente actual
    ticket = support_service.get_ticket_details(ticket_id)
    if not ticket or ticket.agente_id != agent_id:
        flash('No tienes permisos para resolver este ticket.', 'danger')
        return redirect(url_for('support.index'))
    
    # Resolver ticket
    success = support_service.resolve_ticket(ticket_id, resolution_notes)
    
    if success:
        flash('Ticket resuelto correctamente.', 'success')
    else:
        flash('Error al resolver el ticket.', 'danger')
    
    return redirect(url_for('support.index'))

@support_blueprint.route('/tickets/<ticket_id>/close', methods=['POST'])
@login_required
def close_ticket(ticket_id):
    """
    Cierra un ticket definitivamente.
    """
    agent_id = session.get('user_id')
    
    # Verificar que el ticket esté asignado al agente actual o resuelto
    ticket = support_service.get_ticket_details(ticket_id)
    if not ticket:
        flash('Ticket no encontrado.', 'danger')
        return redirect(url_for('support.index'))
    
    if ticket.estado != TicketStatus.RESOLVED and (not ticket.agente_id or ticket.agente_id != agent_id):
        flash('No tienes permisos para cerrar este ticket.', 'danger')
        return redirect(url_for('support.index'))
    
    # Cerrar ticket
    success = support_service.close_ticket(ticket_id)
    
    if success:
        flash('Ticket cerrado correctamente.', 'success')
    else:
        flash('Error al cerrar el ticket.', 'danger')
    
    return redirect(url_for('support.index'))

@support_blueprint.route('/tickets/<ticket_id>/unassign', methods=['POST'])
@login_required
def unassign_ticket(ticket_id):
    """
    Desasigna un ticket.
    """
    agent_id = session.get('user_id')
    
    # Verificar que el ticket esté asignado al agente actual
    ticket = support_service.get_ticket_details(ticket_id)
    if not ticket or ticket.agente_id != agent_id:
        flash('No tienes permisos para desasignar este ticket.', 'danger')
        return redirect(url_for('support.index'))
    
    # Desasignar ticket
    success = support_service.unassign_ticket(ticket_id)
    
    if success:
        flash('Ticket desasignado correctamente.', 'success')
    else:
        flash('Error al desasignar el ticket.', 'danger')
    
    return redirect(url_for('support.index'))

@support_blueprint.route('/tickets/<ticket_id>/message', methods=['POST'])
@login_required
def send_message(ticket_id):
    """
    Envía un mensaje en un ticket.
    """
    agent_id = session.get('user_id')
    agent_name = session.get('user_name')
    message_content = request.form.get('message', '').strip()
    is_internal = request.form.get('is_internal') == 'true'
    
    if not message_content:
        flash('El mensaje no puede estar vacío.', 'danger')
        return redirect(url_for('support.live_chat', ticket_id=ticket_id))
    
    # Verificar que el ticket esté asignado al agente actual
    ticket = support_service.get_ticket_details(ticket_id)
    if not ticket or ticket.agente_id != agent_id:
        flash('No tienes permisos para enviar mensajes en este ticket.', 'danger')
        return redirect(url_for('support.index'))
    
    # Enviar mensaje
    success = support_service.send_message(ticket_id, agent_id, agent_name, message_content, is_internal)
    
    if not success:
        flash('Error al enviar el mensaje.', 'danger')
    
    return redirect(url_for('support.live_chat', ticket_id=ticket_id))

@support_blueprint.route('/api/tickets/pending', methods=['GET'])
@login_required
def api_pending_tickets():
    """
    API para obtener tickets pendientes.
    """
    bank_code = session.get('bank_code')
    
    # Obtener tickets pendientes
    pending_tickets = support_service.get_pending_tickets(bank_code)
    
    # Convertir a formato JSON serializable
    tickets_json = []
    for ticket in pending_tickets:
        tickets_json.append({
            'id': ticket.id,
            'usuario_id': ticket.usuario.id,
            'usuario_nombre': ticket.usuario.nombre or 'Usuario anónimo',
            'fecha_creacion': ticket.fecha_creacion.isoformat(),
            'razon_escalacion': ticket.razon_escalacion.value,
            'prioridad': ticket.prioridad,
            'mensajes_count': len(ticket.conversacion.mensajes) if hasattr(ticket.conversacion, 'mensajes') else 0
        })
    
    return jsonify({
        'status': 'success',
        'tickets': tickets_json
    })

@support_blueprint.route('/api/tickets/assigned', methods=['GET'])
@login_required
def api_assigned_tickets():
    """
    API para obtener tickets asignados al agente actual.
    """
    agent_id = session.get('user_id')
    
    # Obtener tickets asignados
    assigned_tickets = support_service.get_assigned_tickets(agent_id)
    
    # Convertir a formato JSON serializable
    tickets_json = []
    for ticket in assigned_tickets:
        tickets_json.append({
            'id': ticket.id,
            'usuario_id': ticket.usuario.id,
            'usuario_nombre': ticket.usuario.nombre or 'Usuario anónimo',
            'fecha_creacion': ticket.fecha_creacion.isoformat(),
            'fecha_asignacion': ticket.fecha_asignacion.isoformat() if ticket.fecha_asignacion else None,
            'estado': ticket.estado.value,
            'razon_escalacion': ticket.razon_escalacion.value,
            'prioridad': ticket.prioridad,
            'mensajes_count': len(ticket.conversacion.mensajes) if hasattr(ticket.conversacion, 'mensajes') else 0
        })
    
    return jsonify({
        'status': 'success',
        'tickets': tickets_json
    })

@support_blueprint.route('/api/tickets/<ticket_id>/messages', methods=['GET'])
@login_required
def api_ticket_messages(ticket_id):
    """
    API para obtener mensajes de un ticket.
    """
    # Obtener mensajes
    messages = support_service.get_ticket_messages(ticket_id)
    
    # Convertir a formato JSON serializable
    messages_json = []
    for msg in messages:
        messages_json.append({
            'id': msg.get('id'),
            'content': msg.get('content'),
            'sender_id': msg.get('sender_id'),
            'sender_name': msg.get('sender_name'),
            'sender_type': msg.get('sender_type', 'agent'),
            'is_internal': msg.get('is_internal', False),
            'timestamp': msg.get('timestamp').isoformat() if msg.get('timestamp') else None
        })
    
    return jsonify({
        'status': 'success',
        'messages': messages_json
    })

@support_blueprint.route('/api/stats', methods=['GET'])
@login_required
def api_support_stats():
    """
    API para obtener estadísticas de soporte.
    """
    bank_code = session.get('bank_code')
    
    # Obtener estadísticas
    stats = support_service.get_support_stats(bank_code)
    
    # Añadir fecha actual
    stats['timestamp'] = datetime.now().isoformat()
    
    return jsonify({
        'status': 'success',
        'stats': stats
    })

@support_blueprint.route('/api/tickets/<ticket_id>/typing', methods=['POST'])
@login_required
def api_typing_notification(ticket_id):
    """
    API para enviar notificación de escritura.
    """
    agent_id = session.get('user_id')
    agent_name = session.get('user_name')
    is_typing = request.json.get('is_typing', True)
    
    # Verificar que el ticket esté asignado al agente actual
    ticket = support_service.get_ticket_details(ticket_id)
    if not ticket or ticket.agente_id != agent_id:
        return jsonify({
            'status': 'error',
            'message': 'No tienes permisos para este ticket'
        }), 403
    
    # Enviar notificación
    success = support_service.send_typing_notification(ticket_id, agent_id, agent_name, is_typing)
    
    return jsonify({
        'status': 'success' if success else 'error',
        'message': 'Notificación enviada' if success else 'Error al enviar notificación'
    })

@support_blueprint.route('/dashboard', methods=['GET'])
@login_required
def support_dashboard():
    """
    Dashboard para monitoreo de tickets de soporte.
    """
    bank_code = session.get('bank_code')
    bank_name = session.get('bank_name')
    user_name = session.get('user_name')
    
    # Obtener estadísticas
    stats = support_service.get_support_stats(bank_code)
    
    # Obtener tickets recientes
    recent_tickets = support_service.get_recent_tickets(bank_code)
    
    # Obtener datos para gráficos
    chart_data = support_service.get_chart_data(bank_code)
    
    return render_template(
        'support_dashboard.html',
        bank_name=bank_name,
        user_name=user_name,
        stats=stats,
        recent_tickets=recent_tickets,
        chart_data=chart_data
    )