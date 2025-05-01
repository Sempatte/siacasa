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

logger = logging.getLogger(__name__)


class WebApp:
    """
    Aplicación web Flask para interactuar con el chatbot.
    """
    
    def __init__(self, procesar_mensaje_use_case: ProcesarMensajeUseCase):
        """
        Inicializa la aplicación web.
        
        Args:
            procesar_mensaje_use_case: Caso de uso para procesar mensajes
        """
        self.procesar_mensaje_use_case = procesar_mensaje_use_case
        
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
                
                # Procesar mensaje con el chatbot
                respuesta = self.procesar_mensaje_use_case.execute(
                    mensaje_usuario=mensaje,
                    usuario_id=usuario_id,
                    info_usuario=info_usuario
                )
                
                # Devolver respuesta como JSON, incluyendo el ID de usuario
                return jsonify({
                    'respuesta': respuesta,
                    'status': 'success',
                    'usuario_id': usuario_id  # Devolver el ID para que el cliente lo use
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
    
    def run(self, host: str = '0.0.0.0', port: int = 4040, debug: bool = False, **kwargs) -> None:
        """
        Ejecuta la aplicación web.
        
        Args:
            host: Host a utilizar
            port: Puerto a utilizar
            debug: Modo debug
            **kwargs: Argumentos adicionales para Flask
        """
        self.app.run(host=host, port=port, debug=debug, **kwargs)

