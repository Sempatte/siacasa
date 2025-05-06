# admin_panel/main.py
"""
Punto de entrada para el panel de administración SIACASA.

Este archivo permite ejecutar la aplicación del panel de administración
de manera independiente al chatbot principal.
"""

import os
import logging
from dotenv import load_dotenv
from admin_panel.admin_app import AdminPanel

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('admin_panel.log')
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Función principal para iniciar el panel de administración."""
    try:
        # Cargar variables de entorno
        load_dotenv()
        
        # Verificar variables de entorno críticas
        required_vars = ['NEONDB_HOST', 'NEONDB_DATABASE', 'NEONDB_USER', 'NEONDB_PASSWORD']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.error(f"Faltan variables de entorno requeridas: {', '.join(missing_vars)}")
            logger.error("Defina estas variables en el archivo .env o en las variables de entorno del sistema")
            return
        
        # Iniciar la aplicación
        logger.info("Iniciando panel de administración SIACASA")
        admin_panel = AdminPanel()
        
        # Obtener configuración del entorno
        host = os.getenv('ADMIN_HOST', '0.0.0.0')
        port = int(os.getenv('ADMIN_PORT', '5000'))
        debug = os.getenv('ADMIN_DEBUG', 'False').lower() == 'true'
        
        # Ejecutar la aplicación
        admin_panel.run(host=host, port=port, debug=debug)
        
    except Exception as e:
        logger.error(f"Error al iniciar el panel de administración: {e}", exc_info=True)


if __name__ == "__main__":
    main()