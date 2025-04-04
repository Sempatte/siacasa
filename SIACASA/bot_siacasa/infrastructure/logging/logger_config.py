# bot_siacasa/infrastructure/logging/logger_config.py
import os
import logging
from logging.handlers import RotatingFileHandler

def configure_logger(log_level=logging.INFO):
    """
    Configura el logger para la aplicación.
    
    Args:
        log_level: Nivel de logging (default: INFO)
        
    Returns:
        Logger configurado
    """
    # Crear directorio de logs si no existe
    logs_dir = os.path.join(os.getcwd(), 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Configurar logger root
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Limpiar handlers existentes
    if logger.handlers:
        for handler in logger.handlers:
            logger.removeHandler(handler)
    
    # Formato del log
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para archivo (con rotación)
    file_handler = RotatingFileHandler(
        os.path.join(logs_dir, 'siacasa.log'),
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Agregar handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger