# bot_siacasa/infrastructure/websocket/socket_server.py
import logging
import json
import threading
import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Set

import websockets

logger = logging.getLogger(__name__)

class ChatWebSocketServer:
    """
    Servidor WebSocket para chat en tiempo real entre usuarios y agentes de soporte.
    """
    
    def __init__(self, host="0.0.0.0", port=8765):
        """
        Inicializa el servidor WebSocket.
        
        Args:
            host: Host en el que escuchar
            port: Puerto en el que escuchar
        """
        self.host = host
        self.port = port
        self.clients = {}  # client_id -> websocket connection
        self.ticket_subscriptions = {}  # ticket_id -> set of client_ids subscribed
        self.agent_subscriptions = {}  # agent_id -> set of client_ids
        self.user_subscriptions = {}  # user_id -> client_id
        self.running = False
        self.server = None
        
        # Referencia al repositorio de soporte
        self.support_repository = None
    
    def set_support_repository(self, repository):
        """
        Establece el repositorio de soporte para persistencia de mensajes.
        
        Args:
            repository: Instancia del repositorio de soporte
        """
        self.support_repository = repository
    
    async def handler(self, websocket, path):
        """
        Manejador de conexiones WebSocket.
        
        Args:
            websocket: Conexión WebSocket
            path: Ruta de la conexión
        """
        # Generar ID de cliente
        client_id = str(uuid.uuid4())
        self.clients[client_id] = websocket
        
        logger.info(f"Nueva conexión establecida: {client_id}, Path: {path}")
        
        try:
            # Enviar mensaje de bienvenida con ID de cliente
            await websocket.send(json.dumps({
                "type": "welcome",
                "client_id": client_id,
                "timestamp": datetime.now().isoformat()
            }))
            
            # Procesar mensajes
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.process_message(client_id, data)
                except json.JSONDecodeError:
                    logger.warning(f"Mensaje inválido recibido de {client_id}: {message}")
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Formato de mensaje inválido",
                        "timestamp": datetime.now().isoformat()
                    }))
                except Exception as e:
                    logger.error(f"Error al procesar mensaje de {client_id}: {e}", exc_info=True)
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Error al procesar mensaje",
                        "timestamp": datetime.now().isoformat()
                    }))
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Conexión cerrada: {client_id}")
        
        finally:
            # Limpiar suscripciones
            self._cleanup_subscriptions(client_id)
            
            # Eliminar cliente
            if client_id in self.clients:
                del self.clients[client_id]
    
    async def process_message(self, client_id, data):
        """
        Procesa un mensaje recibido.
        
        Args:
            client_id: ID del cliente que envía el mensaje
            data: Datos del mensaje
        """
        message_type = data.get("type")
        
        if message_type == "subscribe_ticket":
            # Suscribir a un ticket
            ticket_id = data.get("ticket_id")
            role = data.get("role", "agent")  # 'agent' o 'user'
            
            if ticket_id:
                await self.subscribe_to_ticket(client_id, ticket_id, role)
            
        elif message_type == "subscribe_agent":
            # Suscribir a notificaciones de un agente
            agent_id = data.get("agent_id")
            
            if agent_id:
                await self.subscribe_to_agent(client_id, agent_id)
            
        elif message_type == "subscribe_user":
            # Suscribir como usuario
            user_id = data.get("user_id")
            
            if user_id:
                await self.subscribe_as_user(client_id, user_id)
            
        elif message_type == "chat_message":
            # Mensaje de chat
            ticket_id = data.get("ticket_id")
            content = data.get("content")
            sender_id = data.get("sender_id")
            sender_name = data.get("sender_name")
            sender_type = data.get("sender_type", "agent")  # 'agent' o 'user'
            is_internal = data.get("is_internal", False)
            
            if ticket_id and content and sender_id:
                await self.broadcast_message(
                    ticket_id, 
                    content, 
                    sender_id, 
                    sender_name,
                    sender_type,
                    is_internal
                )
            
        elif message_type == "typing":
            # Indicador de escritura
            ticket_id = data.get("ticket_id")
            sender_id = data.get("sender_id")
            sender_type = data.get("sender_type", "agent")  # 'agent' o 'user'
            is_typing = data.get("is_typing", True)
            
            if ticket_id and sender_id:
                await self.broadcast_typing(ticket_id, sender_id, sender_type, is_typing)
            
        elif message_type == "read_receipts":
            # Confirmación de lectura
            ticket_id = data.get("ticket_id")
            message_ids = data.get("message_ids", [])
            reader_id = data.get("reader_id")
            
            if ticket_id and message_ids and reader_id:
                await self.broadcast_read_receipts(ticket_id, message_ids, reader_id)
            
        else:
            logger.warning(f"Tipo de mensaje desconocido: {message_type}")
            # Enviar error al cliente
            if client_id in self.clients:
                await self.clients[client_id].send(json.dumps({
                    "type": "error",
                    "message": "Tipo de mensaje desconocido",
                    "timestamp": datetime.now().isoformat()
                }))
    
    async def subscribe_to_ticket(self, client_id, ticket_id, role):
        """
        Suscribe un cliente a un ticket.
        
        Args:
            client_id: ID del cliente
            ticket_id: ID del ticket
            role: Rol del suscriptor ('agent' o 'user')
        """
        # Añadir a suscripciones
        if ticket_id not in self.ticket_subscriptions:
            self.ticket_subscriptions[ticket_id] = set()
        
        self.ticket_subscriptions[ticket_id].add(client_id)
        
        logger.info(f"Cliente {client_id} suscrito al ticket {ticket_id} como {role}")
        
        # Confirmar suscripción
        if client_id in self.clients:
            await self.clients[client_id].send(json.dumps({
                "type": "subscription_confirmed",
                "ticket_id": ticket_id,
                "role": role,
                "timestamp": datetime.now().isoformat()
            }))
    
    async def subscribe_to_agent(self, client_id, agent_id):
        """
        Suscribe un cliente a notificaciones de un agente.
        
        Args:
            client_id: ID del cliente
            agent_id: ID del agente
        """
        # Añadir a suscripciones
        if agent_id not in self.agent_subscriptions:
            self.agent_subscriptions[agent_id] = set()
        
        self.agent_subscriptions[agent_id].add(client_id)
        
        logger.info(f"Cliente {client_id} suscrito al agente {agent_id}")
        
        # Confirmar suscripción
        if client_id in self.clients:
            await self.clients[client_id].send(json.dumps({
                "type": "agent_subscription_confirmed",
                "agent_id": agent_id,
                "timestamp": datetime.now().isoformat()
            }))
    
    async def subscribe_as_user(self, client_id, user_id):
        """
        Suscribe un cliente como usuario.
        
        Args:
            client_id: ID del cliente
            user_id: ID del usuario
        """
        # Añadir a suscripciones
        self.user_subscriptions[user_id] = client_id
        
        logger.info(f"Cliente {client_id} suscrito como usuario {user_id}")
        
        # Confirmar suscripción
        if client_id in self.clients:
            await self.clients[client_id].send(json.dumps({
                "type": "user_subscription_confirmed",
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
            }))
    
    async def broadcast_message(self, ticket_id, content, sender_id, sender_name, sender_type, is_internal=False):
        """
        Envía un mensaje a todos los suscriptores de un ticket.
        
        Args:
            ticket_id: ID del ticket
            content: Contenido del mensaje
            sender_id: ID del remitente
            sender_name: Nombre del remitente
            sender_type: Tipo de remitente ('agent' o 'user')
            is_internal: Indica si el mensaje es interno (solo visible para agentes)
        """
        # Generar ID de mensaje
        message_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # Crear mensaje
        message = {
            "type": "chat_message",
            "message_id": message_id,
            "ticket_id": ticket_id,
            "content": content,
            "sender_id": sender_id,
            "sender_name": sender_name,
            "sender_type": sender_type,
            "is_internal": is_internal,
            "timestamp": timestamp
        }
        
        # Guardar mensaje en la base de datos si es de un agente
        if sender_type == "agent" and self.support_repository:
            try:
                self.support_repository.agregar_mensaje_agente(
                    ticket_id, 
                    sender_id, 
                    sender_name, 
                    content, 
                    is_internal
                )
            except Exception as e:
                logger.error(f"Error al guardar mensaje de agente: {e}", exc_info=True)
        
        # Enviar a todos los suscriptores del ticket
        if ticket_id in self.ticket_subscriptions:
            for client_id in self.ticket_subscriptions[ticket_id]:
                if client_id in self.clients:
                    # No enviar mensajes internos a clientes de usuario
                    if is_internal:
                        # Verificar si el cliente es un agente
                        ws = self.clients[client_id]
                        # TODO: Implementar verificación de rol
                        # Por ahora, asumimos que todos los clientes son agentes
                        await ws.send(json.dumps(message))
                    else:
                        # Mensajes normales se envían a todos
                        await self.clients[client_id].send(json.dumps(message))
        
        # Si el mensaje es de un agente y no es interno, también notificar al usuario
        if sender_type == "agent" and not is_internal:
            # Obtener ID de usuario asociado al ticket
            # TODO: Obtener el usuario_id del ticket desde el repositorio
            # Por ahora, asumimos que no tenemos esta información
            pass
    
    async def broadcast_typing(self, ticket_id, sender_id, sender_type, is_typing=True):
        """
        Envía un indicador de escritura a todos los suscriptores de un ticket.
        
        Args:
            ticket_id: ID del ticket
            sender_id: ID del remitente
            sender_type: Tipo de remitente ('agent' o 'user')
            is_typing: Indica si el remitente está escribiendo
        """
        # Crear mensaje
        message = {
            "type": "typing",
            "ticket_id": ticket_id,
            "sender_id": sender_id,
            "sender_type": sender_type,
            "is_typing": is_typing,
            "timestamp": datetime.now().isoformat()
        }
        
        # Enviar a todos los suscriptores del ticket
        if ticket_id in self.ticket_subscriptions:
            for client_id in self.ticket_subscriptions[ticket_id]:
                if client_id in self.clients:
                    await self.clients[client_id].send(json.dumps(message))
    
    async def broadcast_read_receipts(self, ticket_id, message_ids, reader_id):
        """
        Envía confirmaciones de lectura a todos los suscriptores de un ticket.
        
        Args:
            ticket_id: ID del ticket
            message_ids: Lista de IDs de mensajes leídos
            reader_id: ID del lector
        """
        # Crear mensaje
        message = {
            "type": "read_receipts",
            "ticket_id": ticket_id,
            "message_ids": message_ids,
            "reader_id": reader_id,
            "timestamp": datetime.now().isoformat()
        }
        
        # Enviar a todos los suscriptores del ticket
        if ticket_id in self.ticket_subscriptions:
            for client_id in self.ticket_subscriptions[ticket_id]:
                if client_id in self.clients:
                    await self.clients[client_id].send(json.dumps(message))
    
    def _cleanup_subscriptions(self, client_id):
        """
        Limpia las suscripciones de un cliente.
        
        Args:
            client_id: ID del cliente
        """
        # Limpiar suscripciones de tickets
        for ticket_id, subscribers in list(self.ticket_subscriptions.items()):
            if client_id in subscribers:
                subscribers.remove(client_id)
                # Si no quedan suscriptores, eliminar el ticket
                if not subscribers:
                    del self.ticket_subscriptions[ticket_id]
        
        # Limpiar suscripciones de agentes
        for agent_id, subscribers in list(self.agent_subscriptions.items()):
            if client_id in subscribers:
                subscribers.remove(client_id)
                # Si no quedan suscriptores, eliminar el agente
                if not subscribers:
                    del self.agent_subscriptions[agent_id]
        
        # Limpiar suscripciones de usuarios
        for user_id, subscriber in list(self.user_subscriptions.items()):
            if subscriber == client_id:
                del self.user_subscriptions[user_id]
    
    def start(self):
        """
        Inicia el servidor WebSocket en un hilo separado.
        """
        if self.running:
            logger.warning("El servidor WebSocket ya está en ejecución")
            return
        
        self.running = True
        
        # Crear y arrancar hilo para el servidor
        threading.Thread(target=self._run_server, daemon=True).start()
        
        logger.info(f"Servidor WebSocket iniciado en {self.host}:{self.port}")
    
    def stop(self):
        """
        Detiene el servidor WebSocket.
        """
        if not self.running:
            logger.warning("El servidor WebSocket no está en ejecución")
            return
        
        self.running = False
        
        # Cerrar todas las conexiones
        if self.server:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.server.close())
            loop.close()
        
        logger.info("Servidor WebSocket detenido")
    
    def _run_server(self):
        """
        Ejecuta el servidor WebSocket en un bucle de eventos asyncio.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        start_server = websockets.serve(self.handler, self.host, self.port)
        self.server = loop.run_until_complete(start_server)
        
        try:
            loop.run_forever()
        except Exception as e:
            logger.error(f"Error en el servidor WebSocket: {e}", exc_info=True)
        finally:
            self.server.close()
            loop.run_until_complete(self.server.wait_closed())
            loop.close()


# Instancia global del servidor
chat_socket_server = None

def init_websocket_server(host="0.0.0.0", port=8765, support_repository=None):
    """
    Inicializa y devuelve la instancia global del servidor WebSocket.
    
    Args:
        host: Host en el que escuchar
        port: Puerto en el que escuchar
        support_repository: Repositorio de soporte para persistencia
        
    Returns:
        Instancia del servidor WebSocket
    """
    global chat_socket_server
    
    if chat_socket_server is None:
        chat_socket_server = ChatWebSocketServer(host, port)
        
        if support_repository:
            chat_socket_server.set_support_repository(support_repository)
        
        chat_socket_server.start()
    
    return chat_socket_server

def get_websocket_server():
    """
    Obtiene la instancia global del servidor WebSocket.
    
    Returns:
        Instancia del servidor WebSocket o None si no se ha inicializado
    """
    return chat_socket_server