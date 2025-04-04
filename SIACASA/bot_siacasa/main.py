#!/usr/bin/env python3
"""
Punto de entrada principal para el sistema SIACASA.
Este archivo configura la inyección de dependencias e inicia la aplicación.
"""
import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Importar componentes
from bot_siacasa.infrastructure.logging.logger_config import configure_logger
from bot_siacasa.infrastructure.ai.openai_provider import OpenAIProvider
from bot_siacasa.infrastructure.repositories.memory_repository import MemoryRepository
from bot_siacasa.domain.services.chatbot_service import ChatbotService
from bot_siacasa.application.use_cases.procesar_mensaje_use_case import ProcesarMensajeUseCase
from bot_siacasa.application.use_cases.analizar_sentimiento_use_case import AnalizarSentimientoUseCase
from bot_siacasa.interfaces.cli.cli_app import CLIApp
from bot_siacasa.interfaces.web.web_app import WebApp

def main():
    """Función principal que inicia la aplicación."""
    
    # Configurar logger
    logger = configure_logger()
    logger.info("Iniciando SIACASA...")
    
    # Verificar API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("No se encontró la API key de OpenAI. Configura la variable OPENAI_API_KEY en el archivo .env")
        sys.exit(1)
    
    # Configurar componentes (inyección de dependencias)
    ai_provider = OpenAIProvider(api_key=openai_api_key)
    repository = MemoryRepository()
    
    # Configurar casos de uso
    analizar_sentimiento_use_case = AnalizarSentimientoUseCase(ai_provider)
    
    # Configurar servicio del chatbot
    chatbot_service = ChatbotService(
        repository=repository,
        sentimiento_analyzer=analizar_sentimiento_use_case
    )
    
    # Configurar caso de uso principal
    procesar_mensaje_use_case = ProcesarMensajeUseCase(
        chatbot_service=chatbot_service,
        ai_provider=ai_provider
    )
    
    # Determinar modo de ejecución
    if len(sys.argv) > 1 and sys.argv[1] == "--consola":
        # Modo consola
        app = CLIApp(procesar_mensaje_use_case)
        app.run()
    else:
        # Modo web (por defecto)
        puerto = int(os.environ.get('PORT', 5000))
        app = WebApp(procesar_mensaje_use_case)
        app.run(host='0.0.0.0', port=puerto, debug=True)

if __name__ == "__main__":
    main()