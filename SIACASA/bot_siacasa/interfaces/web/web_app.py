# bot_siacasa/interfaces/web/web_app.py
import os
import uuid
import logging
from typing import Dict, Any
from flask import Flask, render_template, request, jsonify, session

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
                # Obtener datos de la solicitud
                datos = request.json
                mensaje = datos.get('mensaje', '')
                
                # Info adicional del usuario (opcional)
                info_usuario = datos.get('info_usuario', {})
                
                # Obtener ID de usuario de la sesión
                usuario_id = session.get('usuario_id')
                if not usuario_id:
                    usuario_id = str(uuid.uuid4())
                    session['usuario_id'] = usuario_id
                
                # Procesar mensaje con el chatbot
                respuesta = self.procesar_mensaje_use_case.execute(
                    mensaje_usuario=mensaje,
                    usuario_id=usuario_id,
                    info_usuario=info_usuario
                )
                
                # Devolver respuesta como JSON
                return jsonify({
                    'respuesta': respuesta,
                    'status': 'success'
                })
            except Exception as e:
                logger.error(f"Error al procesar mensaje: {e}")
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
    
    def run(self, host: str = '0.0.0.0', port: int = 5000, debug: bool = False, **kwargs) -> None:
        """
        Ejecuta la aplicación web.
        
        Args:
            host: Host a utilizar
            port: Puerto a utilizar
            debug: Modo debug
            **kwargs: Argumentos adicionales para Flask
        """
        self.app.run(host=host, port=port, debug=debug, **kwargs)