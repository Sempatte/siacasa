# bot_siacasa/infrastructure/websocket/socketio_server.py

import logging
import json
import uuid
from datetime import datetime
from typing import Dict, List, Set

from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room

logger = logging.getLogger(__name__)

class ChatSocketIOServer:
    """
    Servidor SocketIO para chat en tiempo real entre usuarios y agentes de soporte.
    """
    
    def __init__(self, app=None, support_repository=None):
        """
        Inicializa el servidor SocketIO.
        
        Args:
            app: Aplicación Flask (opcional)
            support_repository: Repositorio para persistencia de mensajes
        """
        self.socketio = None
        self.support_repository = support_repository
        self.user_connections = {}  # user_id -> session_id
        self.agent_connections = {}  # agent_id -> session_id
        self.ticket_users = {}  # ticket_id -> user_id
        
        # Log when server is initialized
        logger.info("SocketIO server initialized")
        if support_repository:
            logger.info("Support repository provided")
        else:
            logger.warning("No support repository provided, messages won't be persisted")
    
    def init_app(self, socketio):
        """
        Inicializa con la instancia SocketIO creada externamente.
        
        Args:
            socketio: Instancia de SocketIO
        """
        self.socketio = socketio
        self._register_handlers()
        self._load_ticket_users()
        
    def _load_ticket_users(self):
        """
        Carga la relación entre tickets y usuarios desde la base de datos.
        """
        if not self.support_repository or not hasattr(self.support_repository, 'db'):
            logger.warning("No se puede cargar relación ticket-usuario: no hay repositorio")
            return
            
        try:
            query = """
            SELECT id, user_id FROM support_tickets
            """
            results = self.support_repository.db.fetch_all(query)
            
            for row in results:
                self.ticket_users[row['id']] = row['user_id']
                logger.info(f"Relación cargada: ticket {row['id']} -> usuario {row['user_id']}")
        except Exception as e:
            logger.error(f"Error al cargar relaciones ticket-usuario: {e}", exc_info=True)
        
    def _register_handlers(self):
        """
        Registra los manejadores de eventos SocketIO.
        """
        @self.socketio.on('connect')
        def handle_connect():
            logger.info(f"Nueva conexión establecida: {request.sid}")
            emit('welcome', {
                'status': 'success',
                'message': 'Conexión establecida',
                'timestamp': datetime.now().isoformat()
            })
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            logger.info(f"Conexión cerrada: {request.sid}")
            # Limpiar conexiones
            self._cleanup_connection(request.sid)
        
        @self.socketio.on('subscribe_ticket')
        def handle_subscribe_ticket(data):
            logger.info(f"Solicitud de suscripción a ticket: {data}")
            ticket_id = data.get('ticket_id')
            role = data.get('role', 'agent')  # 'agent' o 'user'
            
            if not ticket_id:
                logger.warning("Solicitud de suscripción sin ticket_id")
                emit('error', {
                    'message': 'Se requiere ticket_id',
                    'timestamp': datetime.now().isoformat()
                })
                return
            
            # Suscribir a la sala del ticket
            join_room(f'ticket_{ticket_id}')
            
            # Si este es un agente uniéndose, también enviar mensajes al usuario
            if role == 'agent' and ticket_id in self.ticket_users:
                user_id = self.ticket_users[ticket_id]
                user_room = f'user_{user_id}'
                
                # Enviar notificación de conexión al usuario si está en línea
                if user_id in self.user_connections:
                    self.socketio.emit('agent_connected', {
                        'ticket_id': ticket_id,
                        'message': 'Un agente se ha conectado a tu conversación',
                        'timestamp': datetime.now().isoformat()
                    }, room=user_room)
            
            logger.info(f"Cliente {request.sid} suscrito al ticket {ticket_id} como {role}")
            
            emit('subscription_confirmed', {
                'ticket_id': ticket_id,
                'role': role,
                'timestamp': datetime.now().isoformat()
            })
        
        @self.socketio.on('subscribe_agent')
        def handle_subscribe_agent(data):
            agent_id = data.get('agent_id')
            
            if not agent_id:
                emit('error', {
                    'message': 'Se requiere agent_id',
                    'timestamp': datetime.now().isoformat()
                })
                return
            
            # Guardar asociación de agente -> session_id
            self.agent_connections[agent_id] = request.sid
            
            # Suscribir a la sala del agente
            join_room(f'agent_{agent_id}')
            
            logger.info(f"Cliente {request.sid} suscrito como agente {agent_id}")
            
            emit('agent_subscription_confirmed', {
                'agent_id': agent_id,
                'timestamp': datetime.now().isoformat()
            })
        
        @self.socketio.on('subscribe_user')
        def handle_subscribe_user(data):
            user_id = data.get('user_id')
            
            if not user_id:
                emit('error', {
                    'message': 'Se requiere user_id',
                    'timestamp': datetime.now().isoformat()
                })
                return
            
            # Guardar asociación de usuario -> session_id
            self.user_connections[user_id] = request.sid
            
            # Suscribir a la sala del usuario
            join_room(f'user_{user_id}')
            
            logger.info(f"Cliente {request.sid} suscrito como usuario {user_id}")
            
            emit('user_subscription_confirmed', {
                'user_id': user_id,
                'timestamp': datetime.now().isoformat()
            })
        
        @self.socketio.on('chat_message')
        def handle_chat_message(data):
            try:
                # Log completo de los datos recibidos
                logger.info(f"Mensaje recibido: {data}")
                
                ticket_id = data.get('ticket_id')
                content = data.get('content')
                sender_id = data.get('sender_id')
                sender_name = data.get('sender_name', 'Agente')
                sender_type = data.get('sender_type', 'agent')
                is_internal = data.get('is_internal', False)
                
                if not all([ticket_id, content, sender_id]):
                    logger.warning(f"Datos incompletos en mensaje: {data}")
                    emit('error', {
                        'message': 'Se requieren ticket_id, content y sender_id',
                        'timestamp': datetime.now().isoformat()
                    })
                    return
                
                # Generar ID de mensaje
                message_id = str(uuid.uuid4())
                timestamp = datetime.now().isoformat()
                
                # Crear mensaje
                message = {
                    'type': 'chat_message',
                    'message_id': message_id,
                    'ticket_id': ticket_id,
                    'content': content,
                    'sender_id': sender_id,
                    'sender_name': sender_name,
                    'sender_type': sender_type,
                    'is_internal': is_internal,
                    'timestamp': timestamp
                }
                
                # Guardar mensaje en la base de datos
                if sender_type == "agent" and self.support_repository:
                    try:
                        logger.info(f"Intentando guardar mensaje de agente: {ticket_id}, {sender_id}, {sender_name}")
                        
                        if not hasattr(self.support_repository, 'agregar_mensaje_agente'):
                            logger.error("El repositorio no tiene el método 'agregar_mensaje_agente'")
                            emit('error', {
                                'message': 'Error en la configuración del servidor: método no encontrado',
                                'timestamp': datetime.now().isoformat()
                            })
                            return
                        
                        result = self.support_repository.agregar_mensaje_agente(
                            ticket_id, 
                            sender_id, 
                            sender_name, 
                            content, 
                            is_internal
                        )
                        logger.info(f"Mensaje guardado correctamente: {result}")
                    except Exception as e:
                        logger.error(f"Error al guardar mensaje de agente: {e}", exc_info=True)
                        emit('error', {
                            'message': f'Error al guardar mensaje: {str(e)}',
                            'timestamp': datetime.now().isoformat()
                        })
                        return
                
                # Emitir mensaje a todos los suscriptores del ticket
                ticket_room = f'ticket_{ticket_id}'
                logger.info(f"Emitiendo mensaje a la sala {ticket_room}")
                
                # Si el mensaje no es interno, también enviarlo al usuario directamente
                if not is_internal and ticket_id in self.ticket_users:
                    user_id = self.ticket_users[ticket_id]
                    user_room = f'user_{user_id}'
                    
                    # También emitir a la sala del usuario (widget del chatbot)
                    logger.info(f"Emitiendo mensaje también a la sala {user_room}")
                    
                    # Enviar tanto por socketio como al endpoint REST
                    self.socketio.emit('chat_message', message, room=user_room)
                    
                    # Si hay conexión directa con el widget, intentar enviar directamente
                    if user_id in self.user_connections:
                        logger.info(f"Usuario {user_id} está conectado, enviando mensaje directo")
                        user_sid = self.user_connections[user_id]
                        self.socketio.emit('direct_message', message, room=user_sid)
                
                # Broadcast normal a todos en la sala del ticket
                self.socketio.emit('chat_message', message, room=ticket_room, include_self=False)
                
                # Enviar confirmación al remitente
                emit('message_sent', {
                    'message_id': message_id,
                    'timestamp': timestamp,
                    'status': 'success'
                })
                
                # Registrar mensaje enviado exitosamente
                logger.info(f"Mensaje enviado correctamente a ticket {ticket_id}")
                
            except Exception as e:
                logger.error(f"Error en handle_chat_message: {e}", exc_info=True)
                emit('error', {
                    'message': f'Error en el servidor: {str(e)}',
                    'timestamp': datetime.now().isoformat()
                })
        
        @self.socketio.on('typing')
        def handle_typing(data):
            ticket_id = data.get('ticket_id')
            sender_id = data.get('sender_id')
            sender_type = data.get('sender_type', 'agent')  # 'agent' o 'user'
            is_typing = data.get('is_typing', True)
            
            if not all([ticket_id, sender_id]):
                emit('error', {
                    'message': 'Se requieren ticket_id y sender_id',
                    'timestamp': datetime.now().isoformat()
                })
                return
            
            # Crear mensaje
            message = {
                'type': 'typing',
                'ticket_id': ticket_id,
                'sender_id': sender_id,
                'sender_type': sender_type,
                'is_typing': is_typing,
                'timestamp': datetime.now().isoformat()
            }
            
            # Emitir a todos los suscriptores del ticket
            ticket_room = f'ticket_{ticket_id}'
            self.socketio.emit('typing', message, room=ticket_room, include_self=False)
            
            # También enviar al usuario si es un agente escribiendo
            if sender_type == 'agent' and ticket_id in self.ticket_users:
                user_id = self.ticket_users[ticket_id]
                user_room = f'user_{user_id}'
                self.socketio.emit('typing', message, room=user_room)
    
    def run(self, app, host='0.0.0.0', port=3200, **kwargs):
        """
        Ejecuta el servidor SocketIO.
        
        Args:
            app: Aplicación Flask
            host: Host
            port: Puerto
            kwargs: Argumentos adicionales para socketio.run()
        """
        if self.socketio:
            logger.info(f"Iniciando servidor Socket.IO en {host}:{port}")
            self.socketio.run(app, host=host, port=port, **kwargs)
        else:
            logger.error("No se puede iniciar servidor Socket.IO: no hay instancia SocketIO")
    
    def _cleanup_connection(self, session_id):
        """
        Limpia las conexiones asociadas a un session_id.
        
        Args:
            session_id: ID de sesión a limpiar
        """
        # Limpiar asociaciones de usuario
        for user_id, sid in list(self.user_connections.items()):
            if sid == session_id:
                del self.user_connections[user_id]
                logger.info(f"Conexión de usuario {user_id} removida")
        
        # Limpiar asociaciones de agente
        for agent_id, sid in list(self.agent_connections.items()):
            if sid == session_id:
                del self.agent_connections[agent_id]
                logger.info(f"Conexión de agente {agent_id} removida")


# Instancia global del servidor
socketio_server = None

def init_socketio_server(app=None, support_repository=None):
    """
    Inicializa y devuelve la instancia global del servidor Socket.IO.
    
    Args:
        app: Aplicación Flask (opcional)
        support_repository: Repositorio para persistencia de mensajes
        
    Returns:
        Instancia del servidor Socket.IO
    """
    global socketio_server
    
    if socketio_server is None:
        # Primero crear la instancia de SocketIO con configuración mejorada
        socketio = SocketIO(
            app, 
            cors_allowed_origins="*",  # Permitir todos los orígenes 
            async_mode='eventlet',
            ping_timeout=60,
            ping_interval=25,
            logger=True,  # Habilitar logging detallado
            engineio_logger=True  # Habilitar logging detallado de engineio
        )
        
        # Luego crear el servidor con la clase wrapper
        socketio_server = ChatSocketIOServer(support_repository=support_repository)
        
        # Inicializar el servidor con la instancia de SocketIO
        socketio_server.init_app(socketio)
    
    return socketio_server

# AÑADIR ESTA FUNCIÓN QUE FALTA
def get_websocket_server():
    """
    Obtiene la instancia global del servidor SocketIO.
    
    Returns:
        Instancia del servidor SocketIO o None si no se ha inicializado
    """
    return socketio_server

# AÑADIR ESTA FUNCIÓN PARA COMPATIBILIDAD
def get_socketio_server():
    """
    Alias para get_websocket_server() para mantener compatibilidad.
    
    Returns:
        Instancia del servidor SocketIO o None si no se ha inicializado
    """
    return get_websocket_server()