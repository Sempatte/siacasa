# bot_siacasa/interfaces/web/web_app.py
from datetime import datetime
import os
import uuid
import logging
from typing import Dict, Any
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS  # Necesitarás instalar flask-cors

from bot_siacasa.domain.banks_config import BANK_CONFIGS
from bot_siacasa.application.use_cases.procesar_mensaje_use_case import ProcesarMensajeUseCase
from bot_siacasa.infrastructure.websocket.socketio_server import get_socketio_server

logger = logging.getLogger(__name__)


class WebApp:
    """
    Aplicación web Flask para interactuar con el chatbot.
    """
    
    def __init__(self, procesar_mensaje_use_case: ProcesarMensajeUseCase, chatbot_service):
        """
        Inicializa la aplicación web.
        
        Args:
            procesar_mensaje_use_case: Caso de uso para procesar mensajes
            chatbot_service: Servicio de chatbot para gestionar conversaciones
        """
        self.procesar_mensaje_use_case = procesar_mensaje_use_case
        self.chatbot_service = chatbot_service
        
        # Crear aplicación Flask
        self.app = Flask(
            __name__,
            template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
            static_folder=os.path.join(os.path.dirname(__file__), 'static')
        )
        # En web_app.py, actualiza la configuración CORS:

        CORS(self.app, resources={
            r"/api/*": {
                "origins": [
                    "https://www.bn.com.pe",  # Dominio del Banco de la Nación
                    "https://bn.com.pe",
                    "http://localhost:4040",  # Añadido para desarrollo local
                    "http://127.0.0.1:4040",  # Alternativa para desarrollo local
                    "http://localhost:3200",  # Puerto del embed.js
                    "http://192.168.1.12:3200",  # IP local
                    "http://localhost:*"      # Cualquier puerto en localhost
                ],
                "methods": ["GET", "POST", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization"],
                "supports_credentials": True  # Importante: permite cookies entre dominios
            }
        })

        # Configurar clave secreta para sesiones
        self.app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24))
        
        # Registrar rutas
        self._register_routes()
    
    def _register_routes(self) -> None:
        """
        Registra las rutas de la aplicación.
        """
        # Ruta principal
        @self.app.route('/')
        def index():
            # Generar ID de usuario si no existe
            if 'usuario_id' not in session:
                session['usuario_id'] = str(uuid.uuid4())
            
            return render_template('index.html')
        
        # NUEVO: Añadir método para finalizar una sesión
        @self.app.route('/api/finalizar-sesion', methods=['POST'])
        def finalizar_sesion():
            """
            Finaliza una sesión de chat.
            """
            try:
                # Intenta obtener datos JSON, pero maneja el caso donde no hay datos JSON
                try:
                    datos = request.json
                    usuario_id = datos.get('usuario_id') if datos else None
                except:
                    # Si hay un error al obtener JSON, intenta obtener datos de formulario
                    usuario_id = request.form.get('usuario_id')
                    
                    # Si tampoco hay datos de formulario, intenta obtener datos del cuerpo bruto
                    if not usuario_id and request.data:
                        try:
                            import json
                            raw_data = json.loads(request.data.decode('utf-8'))
                            usuario_id = raw_data.get('usuario_id')
                        except:
                            pass
                
                # Verificación final: si no hay usuario_id, devolver error
                if not usuario_id:
                    logger.warning("Solicitud de finalización de sesión sin ID de usuario")
                    return jsonify({
                        'status': 'error',
                        'mensaje': 'Se requiere ID de usuario'
                    }), 400
                
                logger.info(f"Finalizando sesión para usuario: {usuario_id}")
                
                # Finalizar la sesión activa del usuario
                query = """
                UPDATE chatbot_sessions 
                SET end_time = %s
                WHERE user_id = %s AND end_time IS NULL
                """
                
                from bot_siacasa.infrastructure.db.neondb_connector import NeonDBConnector
                db = NeonDBConnector()
                
                db.execute(query, (datetime.now(), usuario_id))
                logger.info(f"Conversación finalizada para usuario {usuario_id}")
                
                return jsonify({
                    'status': 'success',
                    'mensaje': 'Sesión finalizada correctamente'
                })
                
            except Exception as e:
                logger.error(f"Error al finalizar sesión: {e}", exc_info=True)
                return jsonify({
                    'status': 'error',
                    'mensaje': 'Error al finalizar sesión',
                    'error': str(e)
                }), 500
        
        # API para procesar mensajes
        @self.app.route('/api/mensaje', methods=['POST'])
        def procesar_mensaje():
            try:
                logger.info(f"Recibida solicitud POST a /api/mensaje: {request.json}")
                # Obtener datos de la solicitud
                datos = request.json
                mensaje = datos.get('mensaje', '')
                logger.info(f"Mensaje extraído: '{mensaje}'")
                
                # Info adicional del usuario (opcional)
                info_usuario = datos.get('info_usuario', {})
                
                # CAMBIO: Priorizar el ID de usuario del JSON sobre la sesión
                usuario_id = datos.get('usuario_id')
                
                # Si no hay ID en el JSON, intentar obtenerlo de la sesión
                if not usuario_id:
                    usuario_id = session.get('usuario_id')
                    
                # Si no hay ID en ningún lado, generar uno nuevo
                if not usuario_id:
                    usuario_id = str(uuid.uuid4())
                
                # Guardar el ID en la sesión para futuras solicitudes
                session['usuario_id'] = usuario_id
                logger.info(f"Usando ID de usuario: {usuario_id}")
                
                # Determinar el código del banco desde la solicitud o usar valor predeterminado
                bank_code = datos.get('bank_code', 'default')
                
                # Obtener o crear la conversación
                conversacion = self.chatbot_service.obtener_o_crear_conversacion(usuario_id)

                # NUEVO: Asegurarse de que la conversación tenga el bank_code en sus metadatos
                if hasattr(conversacion, 'metadata'):
                    conversacion.metadata['bank_code'] = bank_code
                elif hasattr(conversacion, 'metadata') and conversacion.metadata is None:
                    conversacion.metadata = {'bank_code': bank_code}

                # Guardar la conversación con los metadatos actualizados
                self.chatbot_service.repository.guardar_conversacion(conversacion)
                
                # NUEVO: Verificar si hay una sesión activa para este usuario o crear una nueva
                session_id = self._get_or_create_chat_session(usuario_id, bank_code)
                
                # Procesar mensaje con el chatbot
                respuesta = self.procesar_mensaje_use_case.execute(
                    mensaje_usuario=mensaje,
                    usuario_id=usuario_id,
                    info_usuario=info_usuario
                )
                
                # NUEVO: Actualizar contador de mensajes en la sesión
                self._update_chat_session_message_count(session_id)
                
                # Devolver respuesta como JSON, incluyendo el ID de usuario
                return jsonify({
                    'respuesta': respuesta,
                    'status': 'success',
                    'usuario_id': usuario_id,  # Devolver el ID para que el cliente lo use
                    'session_id': session_id   # Añadir el ID de sesión para referencia
                })
            except Exception as e:
                logger.error(f"Error al procesar mensaje: {e}", exc_info=True)
                return jsonify({
                    'respuesta': 'Ocurrió un error al procesar tu mensaje.',
                    'error': str(e),
                    'status': 'error'
                }), 500

        
        # Ruta para reiniciar la conversación
        @self.app.route('/api/reiniciar', methods=['POST'])
        def reiniciar_conversacion():
            try:
                # Generar nuevo ID de usuario
                session['usuario_id'] = str(uuid.uuid4())
                
                return jsonify({
                    'mensaje': 'Conversación reiniciada correctamente.',
                    'status': 'success'
                })
            except Exception as e:
                logger.error(f"Error al reiniciar conversación: {e}")
                return jsonify({
                    'mensaje': 'Ocurrió un error al reiniciar la conversación.',
                    'error': str(e),
                    'status': 'error'
                }), 500
        @self.app.route('/api/embed/<bank_code>.js')
        def embed_script(bank_code):
            """Sirve el script de incrustación específico para cada banco."""
            if bank_code not in BANK_CONFIGS:
                return "// Código de banco no válido", 404
                
            # Configurar CORS para este endpoint específico
            response = self.app.make_response(render_template(
                'embed.js', 
                bank=BANK_CONFIGS[bank_code],
                api_url=request.url_root,
                now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            response.headers['Content-Type'] = 'application/javascript'
            return response
        
        
        
    # NUEVO: Añadir métodos de gestión de sesiones
    def _get_or_create_chat_session(self, usuario_id, bank_code):
        """
        Obtiene una sesión de chat activa o crea una nueva.
        
        Args:
            usuario_id: ID del usuario
            bank_code: Código del banco
            
        Returns:
            ID de la sesión
        """
        try:
            # Conectar a la base de datos
            from bot_siacasa.infrastructure.db.neondb_connector import NeonDBConnector
            db = NeonDBConnector()
            
            # PROBLEMA DETECTADO: La consulta solo busca sesiones creadas en los últimos 30 minutos
            # SOLUCIÓN: Buscar cualquier sesión activa (sin end_time) independientemente de cuándo se creó
            
            # Verificar si hay una sesión activa para este usuario (sin end_time)
            query = """
            SELECT id FROM chatbot_sessions 
            WHERE user_id = %s AND bank_code = %s AND end_time IS NULL 
            ORDER BY start_time DESC LIMIT 1
            """
            
            result = db.fetch_one(query, (usuario_id, bank_code))
            
            if result:
                logger.info(f"Sesión activa encontrada: {result['id']} para usuario {usuario_id}")
                return result['id']
            
            # Si no hay sesión activa, crear una nueva
            session_id = str(uuid.uuid4())
            
            query = """
            INSERT INTO chatbot_sessions (id, user_id, bank_code, start_time, message_count, metadata)
            VALUES (%s, %s, %s, %s, 0, %s)
            """
            datos = request.json
            bank_code = datos.get('bank_code', 'default')
            # Metadatos como JSON
            metadata_json = json.dumps({"source": "web"})
            db.execute(query, (session_id, usuario_id, bank_code, datetime.now(), metadata_json))
            logger.info(f"Nueva conversación iniciada: {session_id} para usuario {usuario_id} del banco {bank_code}")
            
            return session_id
            
        except Exception as e:
            logger.error(f"Error al obtener/crear sesión de chat: {e}", exc_info=True)
            # En caso de error, generar un ID de sesión temporal
            return str(uuid.uuid4())
        
    def _update_chat_session_message_count(self, session_id):
        """
        Actualiza el contador de mensajes en una sesión.
        
        Args:
            session_id: ID de la sesión
        """
        try:
            query = """
            UPDATE chatbot_sessions 
            SET message_count = message_count + 1
            WHERE id = %s
            """
            
            from bot_siacasa.infrastructure.db.neondb_connector import NeonDBConnector
            db = NeonDBConnector()
            
            db.execute(query, (session_id,))
            
        except Exception as e:
            logger.error(f"Error al actualizar contador de mensajes: {e}", exc_info=True)

    
    
    def run(self, host: str = '0.0.0.0', port: int = 4040, debug: bool = False, **kwargs) -> None:
        """
        Ejecuta la aplicación web.
        
        Args:
            host: Host a utilizar
            port: Puerto a utilizar
            debug: Modo debug
            **kwargs: Argumentos adicionales para Flask
        """
        # Obtener instancia de SocketIO
        socketio_server = get_socketio_server()
        
        if socketio_server:
            # Si hay SocketIO, usarlo para ejecutar la aplicación
            socketio_server.run(self.app, host=host, port=port, debug=debug, **kwargs)
        else:
            # Si no hay SocketIO, ejecutar normalmente
            self.app.run(host=host, port=port, debug=debug, **kwargs)

