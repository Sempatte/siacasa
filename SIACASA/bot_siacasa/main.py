# app.py o main.py - Punto de entrada principal de la aplicación

import logging
import time
import asyncio
import os
import signal
import sys
from typing import Optional
from dotenv import load_dotenv

# Cargar variables de entorno ANTES de importar las configuraciones
load_dotenv()

# --- Importaciones Requeridas ---
# Clases principales de la aplicación
from bot_siacasa.config.config import OptimizedConfig, EnvironmentConfig, get_optimized_config
from bot_siacasa.domain.services.chatbot_service import ChatbotService
from bot_siacasa.domain.services.response_cache_service import get_cache_service
from bot_siacasa.infrastructure.ai.openai_provider import OpenAIProvider
from bot_siacasa.infrastructure.ai.knowledge_base_service import KnowledgeBaseService
from bot_siacasa.infrastructure.repositories.postgresql_repository import PostgreSQLRepository
from bot_siacasa.application.use_cases.procesar_mensaje_use_case import ProcesarMensajeUseCase
from bot_siacasa.application.use_cases.analizar_sentimiento_use_case import AnalizarSentimientoUseCase

# Componentes para el servidor web
from flask import Flask, jsonify, request, render_template_string
from bot_siacasa.infrastructure.websocket.socketio_server import init_socketio_server
from bot_siacasa.infrastructure.db.neondb_connector import NeonDBConnector
from bot_siacasa.infrastructure.db.support_repository import SupportRepository
from bot_siacasa.interfaces.web.web_app import WebApp

# Configurar logging optimizado
logging.basicConfig(
    level=getattr(logging, EnvironmentConfig.LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BANK_PROFILES = {
    "bn": {
        "bank_name": "Banco de la Nación (Demo)",
        "style": "formal",
        "greeting": "Hola, soy el asistente virtual del Banco de la Nación. ¿En qué puedo ayudarte hoy?",
        "identity_statement": (
            "Representas al Banco de la Nación del Perú en un entorno de pruebas QA. "
            "Debes ofrecer información oficial sobre agencias, horarios, canales y servicios, "
            "y nunca indicar que careces de afiliación bancaria."
        )
    }
}


class OptimizedChatbotApp:
    """
    Aplicación principal del chatbot optimizada para máximo rendimiento.
    """
    
    def __init__(self):
        """Inicializa la aplicación con configuración optimizada."""
        self.config = get_optimized_config()
        self.cache_service = get_cache_service()
        
        # Componentes principales
        self.repository = None
        self.repository_backend = "uninitialized"
        self.persistence_enabled = False
        self.repository_error = None
        self.ai_provider = None
        self.knowledge_service = None
        self.chatbot_service = None
        self.procesar_mensaje_use_case = None
        
        # Métricas de rendimiento
        self.start_time = time.time()
        self.total_requests = 0
        self.total_response_time = 0.0
        
        logger.info("🚀 Inicializando OptimizedChatbotApp...")
    
    def initialize(self) -> None:
        """Inicializa todos los componentes de la aplicación."""
        init_start = time.perf_counter()
        
        try:
            # 1. Inicializar conector de base de datos y repositorio PERSISTENTE
            neon_disabled = EnvironmentConfig.DISABLE_NEONDB or EnvironmentConfig.USE_MEMORY_REPOSITORY
            repo_issue = None

            if neon_disabled:
                repo_issue = "NeonDB deshabilitado por configuración"
                logger.warning("NeonDB deshabilitado vía variable de entorno. Se utilizará el repositorio en memoria.")
            else:
                try:
                    db_connector = NeonDBConnector(
                        connect_timeout=EnvironmentConfig.NEONDB_CONNECT_TIMEOUT
                    )
                    self.repository = PostgreSQLRepository(db_connector)
                    self.repository_backend = "postgresql"
                    self.persistence_enabled = True
                    self.repository_error = None
                    logger.info("✅ PostgreSQL Repository inicializado")
                except Exception as db_error:
                    repo_issue = f"{db_error.__class__.__name__}: {db_error}"
                    self.repository_error = repo_issue
                    logger.warning(
                        "No se pudo conectar a NeonDB. Se usará repositorio en memoria. Detalle: %s",
                        db_error,
                        exc_info=True
                    )

            if self.repository is None:
                from bot_siacasa.infrastructure.repositories.memory_repository import MemoryRepository

                self.repository = MemoryRepository()
                self.repository_backend = "memory"
                self.persistence_enabled = False
                self.repository_error = repo_issue
                logger.warning(
                    "⚠️ Usando repositorio en memoria (sin persistencia). Motivo: %s",
                    repo_issue or "no se proporcionó"
                )

            
            # 2. Inicializar proveedor de IA con configuración optimizada
            if not EnvironmentConfig.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY no configurada")
            
            self.ai_provider = OpenAIProvider(
                api_key=EnvironmentConfig.OPENAI_API_KEY,
                model=self.config["openai"]["model"]
            )
            # Aplicar configuración optimizada
            self.ai_provider.update_config(**self.config["openai"])
            logger.info(f"✅ OpenAI Provider inicializado con modelo {self.config['openai']['model']}")

            # 2b. Inicializar servicio de conocimiento vectorial si hay persistencia
            if self.persistence_enabled and isinstance(self.repository, PostgreSQLRepository):
                try:
                    default_bank_code = getattr(EnvironmentConfig, "BANK_CODE", "default")
                    self.knowledge_service = KnowledgeBaseService(
                        db_connector=self.repository.db,
                        ai_provider=self.ai_provider,
                        default_bank_code=default_bank_code or "default"
                    )
                    logger.info("✅ KnowledgeBaseService inicializado")
                except Exception as kb_error:
                    self.knowledge_service = None
                    logger.warning(
                        "No se pudo inicializar el KnowledgeBaseService. Se continuará sin contexto enriquecido. Detalle: %s",
                        kb_error,
                        exc_info=True
                    )
            else:
                self.knowledge_service = None
                logger.warning("Knowledge base deshabilitada (sin base de datos persistente disponible).")
            
            # 3. Inicializar analizador de sentimientos
            sentiment_analyzer = AnalizarSentimientoUseCase(self.ai_provider)
            logger.info("✅ Sentiment Analyzer inicializado")
            
            # 4. Inicializar servicio principal del chatbot
            bank_code = getattr(EnvironmentConfig, "BANK_CODE", "default")
            bank_profile = BANK_PROFILES.get(bank_code.lower(), {})
            default_bank_name = bank_profile.get("bank_name", "SIACASA Bank")
            bank_config = {
                "bank_name": default_bank_name,
                "style": bank_profile.get("style", "professional"),
                "greeting": bank_profile.get(
                    "greeting",
                    "Hola, soy tu asistente virtual bancario. ¿En qué puedo ayudarte hoy?"
                ),
                "identity_statement": bank_profile.get(
                    "identity_statement",
                    f"Representas al banco {default_bank_name} para resolver consultas oficiales."
                ),
                "bank_code": bank_code
            }

            self.chatbot_service = ChatbotService(
                repository=self.repository,
                sentimiento_analyzer=sentiment_analyzer,
                ai_provider=self.ai_provider,
                bank_config=bank_config,
                knowledge_service=self.knowledge_service
            )
            logger.info("✅ ChatbotService inicializado")
            
            # 5. Inicializar caso de uso principal
            self.procesar_mensaje_use_case = ProcesarMensajeUseCase(
                chatbot_service=self.chatbot_service
            )
            logger.info("✅ ProcesarMensajeUseCase inicializado")
            
            init_time = (time.perf_counter() - init_start) * 1000
            logger.info(f"🎉 Aplicación inicializada completamente en {init_time:.2f}ms")
            
        except Exception as e:
            init_time = (time.perf_counter() - init_start) * 1000
            logger.error(f"❌ Error inicializando aplicación ({init_time:.2f}ms): {e}", exc_info=True)
            raise
    
    def process_message(self, user_id: str, message: str) -> str:
        """
        Procesa un mensaje de usuario de forma optimizada.
        """
        request_start = time.perf_counter()
        self.total_requests += 1
        
        try:
            if not message or not message.strip():
                return "Por favor, escribe un mensaje para poder ayudarte."
            
            if not user_id:
                user_id = f"anonymous_{int(time.time())}"
            
            cache_key = self.cache_service.generate_key(user_id, message)
            cached_response = self.cache_service.get_response(cache_key)
            
            if cached_response:
                response_time = (time.perf_counter() - request_start) * 1000
                logger.info(f"⚡ Respuesta del cache en {response_time:.2f}ms")
                self._update_metrics(response_time)
                return cached_response
            
            response = self.procesar_mensaje_use_case.execute(
                mensaje_usuario=message,
                usuario_id=user_id
            )
            
            category = self.cache_service.categorize_message(message)
            self.cache_service.set_response(cache_key, response, category)
            
            response_time = (time.perf_counter() - request_start) * 1000
            self._update_metrics(response_time)
            
            logger.info(f"✅ Mensaje procesado en {response_time:.2f}ms (total: {self.total_requests})")
            
            return response
            
        except Exception as e:
            response_time = (time.perf_counter() - request_start) * 1000
            logger.error(f"❌ Error procesando mensaje ({response_time:.2f}ms): {e}", exc_info=True)
            return "Lo siento, estoy experimentando problemas técnicos. Por favor, intenta de nuevo."
    
    def get_performance_stats(self) -> dict:
        """Retorna estadísticas de rendimiento."""
        uptime = time.time() - self.start_time
        avg_response_time = (self.total_response_time / max(self.total_requests, 1))
        
        return {
            "uptime_seconds": round(uptime, 2),
            "total_requests": self.total_requests,
            "avg_response_time_ms": round(avg_response_time, 2),
            "requests_per_second": round(self.total_requests / max(uptime, 1), 2),
            "cache_stats": self.cache_service.get_stats(),
            "ai_provider_stats": self.ai_provider.get_cache_stats() if hasattr(self.ai_provider, 'get_cache_stats') else {},
            "repository_backend": self.repository_backend,
            "persistence_enabled": self.persistence_enabled,
            "knowledge_base_enabled": self.knowledge_service is not None,
            "repository_issue": self.repository_error
        }

    def _update_metrics(self, response_time_ms: float) -> None:
        """Actualiza métricas internas."""
        self.total_response_time += response_time_ms

    def health_check(self) -> dict:
        """Verifica el estado de la aplicación."""
        try:
            test_response = self.process_message("health_check", "hola")
            return { "status": "healthy", "timestamp": time.time() }
        except Exception as e:
            return { "status": "unhealthy", "error": str(e) }

# --- Singleton y Funciones de Servidor ---
app_instance: Optional[OptimizedChatbotApp] = None

def get_app() -> OptimizedChatbotApp:
    """Retorna la instancia global de la aplicación (singleton)."""
    global app_instance
    if app_instance is None:
        app_instance = OptimizedChatbotApp()
        app_instance.initialize()
    return app_instance

def main():
    """Función principal para ejecutar la aplicación como SERVIDOR WEB."""
    print("🚀 Iniciando SIACASA Chatbot Optimizado como Servidor Web...")
    
    try:
        # Inicializar aplicación
        app = get_app()

        if not app.persistence_enabled:
            logger.warning("La aplicación se está ejecutando sin persistencia de NeonDB.")
            print("⚠️ NeonDB no disponible o deshabilitado. Usando repositorio en memoria (los datos no se persistirán).")
        
        # Crear la aplicación web Flask
        web_app_instance = WebApp(app.procesar_mensaje_use_case, app.chatbot_service)
        
        # Inicializar el repositorio de soporte para Socket.IO
        support_repository = None
        if app.persistence_enabled and isinstance(app.repository, PostgreSQLRepository):
            try:
                support_repository = SupportRepository(app.repository.db)
                logger.info("Repositorio de soporte inicializado utilizando NeonDB.")
            except Exception as support_error:
                logger.warning(
                    "No se pudo inicializar el repositorio de soporte. El chat en vivo funcionará sin persistencia. Detalle: %s",
                    support_error,
                    exc_info=True
                )
        else:
            logger.warning("Repositorio de soporte deshabilitado porque no hay base de datos persistente disponible.")
        
        # Inicializar el servidor Socket.IO
        socketio_server = init_socketio_server(web_app_instance.app, support_repository)
        if support_repository is None:
            logger.warning("Socket.IO se ejecutará sin soporte para tickets persistentes.")
        
        # Usar la configuración de config.py para el puerto y host
        host = EnvironmentConfig.HOST
        port = EnvironmentConfig.PORT
        debug = EnvironmentConfig.DEBUG
        
        logger.info(f"🌐 Iniciando servidor en http://{host}:{port} (Debug: {debug})")
        print(f"✅ Servidor SIACASA corriendo en http://{host}:{port}")
        print("   - API en /api/mensaje")
        print("   - Widget en /")
        print("\n🔄 Servidor activo. Presiona Ctrl+C para detener.")
        
        # Ejecutar el servidor Socket.IO, que maneja la aplicación Flask
        socketio_server.run(web_app_instance.app, host=host, port=port, debug=debug, use_reloader=False)

    except ValueError as e:
        logger.error(f"❌ Error de configuración: {e}")
        print(f"❌ Error de configuración: {e}. Asegúrate de que OPENAI_API_KEY está en tu archivo .env")
        exit(1)
    except Exception as e:
        logger.error(f"❌ Error fatal al iniciar el servidor: {e}", exc_info=True)
        print(f"❌ Error fatal: {e}")
        exit(1)

if __name__ == "__main__":
    main()
