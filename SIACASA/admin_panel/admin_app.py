# admin_panel/admin_app.py
import os
import logging
from flask import Flask, render_template, redirect, url_for, flash, request, session
from functools import wraps
from dotenv import load_dotenv

# Importar módulos del panel de administración
from admin_panel.auth.auth_controller import auth_blueprint
from admin_panel.training.training_controller import training_blueprint
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
        self.app.register_blueprint(auth_blueprint)
        self.app.register_blueprint(training_blueprint, url_prefix='/training')
        
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
            
            # Obtener estadísticas básicas
            stats = {
                'total_conversations': self.db.get_conversation_count(bank_code),
                'total_training_files': self.db.get_training_file_count(bank_code),
                'last_training': self.db.get_last_training_date(bank_code),
                'active_users': self.db.get_active_user_count(bank_code)
            }
            
            return render_template(
                'dashboard.html',
                bank_name=bank_name,
                stats=stats,
                user_name=session.get('user_name', 'Admin')
            )
        
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