# app.py o main.py - Punto de entrada principal de la aplicación

import os
import logging
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('chatbot.log')
    ]
)

logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# Importar componentes necesarios
from bot_siacasa.domain.services.chatbot_service import ChatbotService
from bot_siacasa.infrastructure.repositories.memory_repository import MemoryRepository
from bot_siacasa.infrastructure.ai.openai_provider import OpenAIProvider
from bot_siacasa.application.use_cases.analizar_sentimiento_use_case import AnalizarSentimientoUseCase
from bot_siacasa.application.use_cases.procesar_mensaje_use_case import ProcesarMensajeUseCase
from bot_siacasa.domain.banks_config import BANK_CONFIGS
from bot_siacasa.interfaces.web.web_app import WebApp
from bot_siacasa.domain.entities.analisis_sentimiento import AnalisisSentimiento
from bot_siacasa.infrastructure.db.support_repository import SupportRepository
from bot_siacasa.infrastructure.websocket.socket_server import init_websocket_server

def main():
    """Función principal para iniciar la aplicación."""
    try:
        logger.info("Iniciando aplicación SIACASA")
        
        # Obtener configuración
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            logger.error("No se encontró la API key de OpenAI. Configura la variable de entorno OPENAI_API_KEY.")
            return
        
        # Configuración del banco (default: Banco de la Nación)
        bank_code = os.getenv("BANK_CODE", "bn")
        bank_config = BANK_CONFIGS.get(bank_code)
        
        logger.info(f"Usando configuración para banco: {bank_config['bank_name']}")
        
        # Crear el repositorio
        repository = MemoryRepository()
        logger.info("Repositorio en memoria inicializado")
        
        # Inicializar repositorio de soporte
        support_repository = SupportRepository(db_connector)
        logger.info("Repositorio de soporte inicializado")
        
         # Iniciar servidor WebSocket para chat en tiempo real
        websocket_server = init_websocket_server(host="0.0.0.0", port=8765, support_repository=support_repository)
        logger.info("Servidor WebSocket iniciado en 0.0.0.0:8765")
        
        # Crear el proveedor de IA de OpenAI
        ai_provider = OpenAIProvider(
            api_key=openai_api_key,
            model=os.getenv("OPENAI_MODEL", "gpt-4o")
        )
        logger.info(f"Proveedor de OpenAI inicializado con modelo {ai_provider.model}")
        
        # Crear el analizador de sentimientos
        sentimiento_analyzer = AnalizarSentimientoUseCase(ai_provider)
        logger.info("Analizador de sentimientos inicializado")
        
        # Crear el servicio de chatbot
        chatbot_service = ChatbotService(
            repository=repository,
            sentimiento_analyzer=sentimiento_analyzer,
            ai_provider=ai_provider,  # IMPORTANTE: pasar el proveedor de IA
            bank_config=bank_config,
            support_repository=support_repository  # Añadir repositorio de soporte
        )
        logger.info("Servicio de chatbot inicializado")
        
        # Crear el caso de uso para procesar mensajes
        procesar_mensaje_use_case = ProcesarMensajeUseCase(
            chatbot_service=chatbot_service,
            ai_provider=ai_provider
        )
        logger.info("Caso de uso para procesar mensajes inicializado")
        
        # Crear la aplicación web
        app = WebApp(procesar_mensaje_use_case=procesar_mensaje_use_case)
        logger.info("Aplicación web inicializada")
        
        # Ejecutar la aplicación
        host = os.getenv("HOST", "0.0.0.0")
        port = int(os.getenv("PORT", "3200"))
        debug = os.getenv("DEBUG", "False").lower() == "true"
        
        logger.info(f"Iniciando servidor en {host}:{port} (debug={debug})")
        app.run(host=host, port=port, debug=debug)
        
    except Exception as e:
        logger.error(f"Error al iniciar la aplicación: {e}", exc_info=True)

if __name__ == "__main__":
    main()