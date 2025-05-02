# admin_panel/admin_app.py
from datetime import datetime
import os
import logging
from flask import Flask, jsonify, render_template, redirect, url_for, flash, request, session
from functools import wraps
from dotenv import load_dotenv

# Importar módulos del panel de administración
from admin_panel.auth.auth_controller import auth_blueprint
from admin_panel.training.training_controller import training_blueprint
from admin_panel.auth.auth_middleware import login_required
from admin_panel.auth.auth_controller import auth_blueprint
from admin_panel.training.training_controller import training_blueprint
from admin_panel.support.support_controller import support_blueprint
from admin_panel.auth.auth_middleware import login_required

# Importar conector de base de datos
from bot_siacasa.infrastructure.db.neondb_connector import NeonDBConnector

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

class AdminPanel:
    """
    Aplicación web Flask para el panel de administración del chatbot.
    """
    
    def __init__(self):
        """
        Inicializa la aplicación del panel de administración.
        """
        # Crear aplicación Flask
        self.app = Flask(
            __name__,
            template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
            static_folder=os.path.join(os.path.dirname(__file__), 'static')
        )
        
        # Configurar clave secreta para sesiones
        self.app.secret_key = os.getenv('ADMIN_SECRET_KEY', os.urandom(24))
        
        # Configurar tiempo de expiración de sesión (30 minutos)
        self.app.config['PERMANENT_SESSION_LIFETIME'] = 1800
        
        # Inicializar conexión a base de datos
        self.db = NeonDBConnector(
            host=os.getenv('NEONDB_HOST'),
            database=os.getenv('NEONDB_DATABASE'),
            user=os.getenv('NEONDB_USER'),
            password=os.getenv('NEONDB_PASSWORD')
        )
        
        # Configurar carpeta de carga de archivos
        self.app.config['UPLOAD_FOLDER'] = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            'uploads',
            'training'
        )
        
        # Asegurar que la carpeta de carga exista
        os.makedirs(self.app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        # Registrar blueprints
        self.app.register_blueprint(training_blueprint, url_prefix='/training')
        self.app.register_blueprint(auth_blueprint)
        self.app.register_blueprint(support_blueprint, url_prefix='/support')
        
        # Registrar rutas
        self._register_routes()
    
    def _register_routes(self):
        """
        Registra las rutas de la aplicación.
        """
        @self.app.route('/')
        def index():
            """Redirecciona a login o dashboard según el estado de autenticación."""
            if 'user_id' in session:
                return redirect(url_for('dashboard'))
            return redirect(url_for('auth.login'))
        
        @self.app.route('/dashboard')
        @login_required
        def dashboard():
            """Muestra el dashboard principal del panel de administración."""
            # Obtener información del banco
            bank_code = session.get('bank_code', 'default')
            bank_name = session.get('bank_name', 'Banco')
            
            # Obtener estadísticas reales desde la base de datos
            try:
                # Obtener total de conversaciones/sesiones (no mensajes)
                # NOTA: Cada registro en chatbot_sessions es una conversación
                query = """
                SELECT COUNT(*) as count 
                FROM chatbot_sessions 
                WHERE bank_code = %s
                """
                total_conversations = self.db.fetch_one(query, (bank_code,))
                conversation_count = total_conversations['count'] if total_conversations else 0
                
                # Obtener usuarios activos en las últimas 24 horas
                query = """
                SELECT COUNT(DISTINCT user_id) as count 
                FROM chatbot_sessions 
                WHERE bank_code = %s 
                AND (
                    -- Sesiones que comenzaron en las últimas 24 horas
                    start_time > NOW() - INTERVAL '24 hours'
                    OR 
                    -- Sesiones que tuvieron actividad en las últimas 24 horas
                    last_activity_time > NOW() - INTERVAL '24 hours'
                    OR
                    -- Sesiones que terminaron en las últimas 24 horas
                    (end_time IS NOT NULL AND end_time > NOW() - INTERVAL '24 hours')
                )
                """
                active_users = self.db.fetch_one(query, (bank_code,))
                active_users_count = active_users['count'] if active_users else 0
                
                # Obtener archivos de entrenamiento
                query = "SELECT COUNT(*) as count FROM training_files WHERE bank_code = %s"
                training_files = self.db.fetch_one(query, (bank_code,))
                training_files_count = training_files['count'] if training_files else 0
                
                # Obtener última fecha de entrenamiento
                query = """
                SELECT end_time 
                FROM training_sessions 
                WHERE bank_code = %s AND status = 'completed'
                ORDER BY end_time DESC
                LIMIT 1
                """
                last_training = self.db.fetch_one(query, (bank_code,))
                last_training_date = last_training['end_time'] if last_training else None
                
                # Crear diccionario de estadísticas
                stats = {
                    'total_conversations': conversation_count,
                    'total_training_files': training_files_count,
                    'last_training': last_training_date,
                    'active_users': active_users_count
                }
            except Exception as e:
                logger.error(f"Error al obtener estadísticas: {e}", exc_info=True)
                # En caso de error, mostrar valores por defecto
                stats = {
                    'total_conversations': 0,
                    'total_training_files': 0,
                    'last_training': None,
                    'active_users': 0
                }
            
            return render_template(
                'dashboard.html',
                bank_name=bank_name,
                stats=stats,
                user_name=session.get('user_name', 'Admin')
            )

        @self.app.route('/api/dashboard/stats')
        @login_required
        def dashboard_stats():
            """API para obtener estadísticas actualizadas del dashboard."""
            bank_code = session.get('bank_code', 'default')
            
            try:
                # Obtener total de conversaciones
                query = "SELECT COUNT(*) as count FROM chatbot_sessions WHERE bank_code = %s"
                total_conversations = self.db.fetch_one(query, (bank_code,))
                conversation_count = total_conversations['count'] if total_conversations else 0
                
                # Obtener usuarios activos en las últimas 24 horas
                query = """
                SELECT COUNT(DISTINCT user_id) as count 
                FROM chatbot_sessions 
                WHERE bank_code = %s AND start_time > NOW() - INTERVAL '24 hours'
                """
                active_users = self.db.fetch_one(query, (bank_code,))
                active_users_count = active_users['count'] if active_users else 0
                
                return jsonify({
                    'total_conversations': conversation_count,
                    'active_users': active_users_count,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Error al obtener estadísticas API: {e}", exc_info=True)
                return jsonify({
                    'error': 'Error al obtener estadísticas',
                    'timestamp': datetime.now().isoformat()
                }), 500
        # Añadir endpoint para estadísticas detalladas (para página de análisis)
        @self.app.route('/api/dashboard/detailed-stats')
        @login_required
        def detailed_stats():
            """API para obtener estadísticas detalladas."""
            bank_code = session.get('bank_code', 'default')
            
            try:
                # Conversaciones por día (últimos 7 días)
                query = """
                SELECT 
                    DATE(start_time) as date, 
                    COUNT(*) as count
                FROM 
                    chatbot_sessions
                WHERE 
                    bank_code = %s
                    AND start_time > NOW() - INTERVAL '7 days'
                GROUP BY 
                    DATE(start_time)
                ORDER BY 
                    date DESC
                """
                conversations_by_day = self.db.fetch_all(query, (bank_code,))
                
                # Duración promedio de conversaciones
                query = """
                SELECT 
                    AVG(EXTRACT(EPOCH FROM (end_time - start_time))) as avg_duration
                FROM 
                    chatbot_sessions
                WHERE 
                    bank_code = %s
                    AND end_time IS NOT NULL
                """
                duration_result = self.db.fetch_one(query, (bank_code,))
                avg_duration = round(float(duration_result['avg_duration']), 0) if duration_result and duration_result['avg_duration'] else 0
                
                # Convertir a formato de minutos y segundos
                avg_duration_formatted = f"{int(avg_duration // 60)} min {int(avg_duration % 60)} seg"
                
                # Distribución de mensajes por conversación
                query = """
                SELECT 
                    CASE
                        WHEN message_count BETWEEN 1 AND 2 THEN '1-2'
                        WHEN message_count BETWEEN 3 AND 5 THEN '3-5'
                        WHEN message_count BETWEEN 6 AND 10 THEN '6-10'
                        ELSE '10+'
                    END as range,
                    COUNT(*) as count
                FROM 
                    chatbot_sessions
                WHERE 
                    bank_code = %s
                GROUP BY 
                    range
                ORDER BY 
                    range
                """
                message_distribution = self.db.fetch_all(query, (bank_code,))
                
                return jsonify({
                    'conversations_by_day': conversations_by_day,
                    'avg_duration': avg_duration_formatted,
                    'message_distribution': message_distribution,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Error al obtener estadísticas detalladas: {e}", exc_info=True)
                return jsonify({
                    'error': 'Error al obtener estadísticas detalladas',
                    'timestamp': datetime.now().isoformat()
                }), 500
                
        @self.app.route('/api/admin/cerrar-sesiones-inactivas', methods=['POST'])
        @login_required  # Asegúrate de que esta ruta esté protegida
        def cerrar_sesiones_inactivas():
            """
            Cierra sesiones que han estado inactivas por más de 30 minutos.
            Utiliza la última actualización de message_count como referencia.
            """
            try:
                # Obtener sesiones inactivas
                # PROBLEMA CORREGIDO: Ahora usa last_activity_time para determinar la inactividad
                query = """
                UPDATE chatbot_sessions 
                SET end_time = NOW()
                WHERE end_time IS NULL 
                AND (
                    -- Cerrar sesiones donde no ha habido actividad en 30 minutos
                    last_activity_time < NOW() - INTERVAL '30 minutes'
                    OR
                    -- Si no hay last_activity_time, usar start_time
                    (last_activity_time IS NULL AND start_time < NOW() - INTERVAL '30 minutes')
                )
                RETURNING id
                """
                
                from bot_siacasa.infrastructure.db.neondb_connector import NeonDBConnector
                db = NeonDBConnector()
                
                result = db.fetch_all(query)
                
                sessions_closed = len(result) if result else 0
                
                return jsonify({
                    'status': 'success',
                    'mensaje': f'Se cerraron {sessions_closed} sesiones inactivas',
                    'sessions_closed': sessions_closed
                })
                
            except Exception as e:
                logger.error(f"Error al cerrar sesiones inactivas: {e}", exc_info=True)
                return jsonify({
                    'status': 'error',
                    'mensaje': 'Error al cerrar sesiones inactivas',
                    'error': str(e)
                }), 500
        
        @self.app.route('/logout')
        def logout():
            """Cierra la sesión del usuario."""
            session.clear()
            flash('Has cerrado sesión correctamente.', 'success')
            return redirect(url_for('auth.login'))
        
        @self.app.errorhandler(404)
        def page_not_found(e):
            """Maneja errores 404."""
            return render_template('error.html', error_code=404, message="Página no encontrada"), 404
        
        @self.app.errorhandler(500)
        def server_error(e):
            """Maneja errores 500."""
            logger.error(f"Error del servidor: {e}")
            return render_template('error.html', error_code=500, message="Error interno del servidor"), 500
    
    def run(self, host='0.0.0.0', port=5000, debug=False, **kwargs):
        """
        Ejecuta la aplicación del panel de administración.
        
        Args:
            host: Host a utilizar
            port: Puerto a utilizar
            debug: Modo debug
            **kwargs: Argumentos adicionales para Flask
        """
        admin_port = int(os.getenv('ADMIN_PORT', port))
        admin_host = os.getenv('ADMIN_HOST', host)
        admin_debug = os.getenv('ADMIN_DEBUG', str(debug)).lower() == 'true'
        
        logger.info(f"Iniciando panel de administración en {admin_host}:{admin_port} (debug={admin_debug})")
        self.app.run(host=admin_host, port=admin_port, debug=admin_debug, **kwargs)


# Punto de entrada para ejecución directa
if __name__ == "__main__":
    admin_panel = AdminPanel()
    admin_panel.run()