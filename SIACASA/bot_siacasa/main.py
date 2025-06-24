# main.py
import logging
import time
import asyncio
from typing import Optional

from bot_siacasa.config.config import OptimizedConfig, EnvironmentConfig, get_optimized_config
from bot_siacasa.domain.services.chatbot_service import ChatbotService
from bot_siacasa.domain.services.response_cache_service import get_cache_service
from bot_siacasa.infrastructure.ai.openai_provider import OpenAIProvider
from bot_siacasa.infrastructure.repositories.memory_repository import MemoryRepository
from bot_siacasa.application.use_cases.procesar_mensaje_use_case import ProcesarMensajeUseCase
from bot_siacasa.application.use_cases.analizar_sentimiento_use_case import AnalizarSentimientoUseCase

# Configurar logging optimizado
logging.basicConfig(
    level=getattr(logging, EnvironmentConfig.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
        self.ai_provider = None
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
            # 1. Inicializar repositorio
            self.repository = MemoryRepository()
            logger.info("✅ Repository inicializado")
            
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
            
            # 3. Inicializar analizador de sentimientos
            sentiment_analyzer = AnalizarSentimientoUseCase(self.ai_provider)
            logger.info("✅ Sentiment Analyzer inicializado")
            
            # 4. Inicializar servicio principal del chatbot
            self.chatbot_service = ChatbotService(
                repository=self.repository,
                sentimiento_analyzer=sentiment_analyzer,
                ai_provider=self.ai_provider,
                bank_config={
                    "bank_name": "SIACASA Bank",
                    "style": "professional"
                }
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
        
        Args:
            user_id: ID del usuario
            message: Mensaje del usuario
            
        Returns:
            Respuesta del chatbot
        """
        request_start = time.perf_counter()
        self.total_requests += 1
        
        try:
            # Validación rápida
            if not message or not message.strip():
                return "Por favor, escribe un mensaje para poder ayudarte."
            
            if not user_id:
                user_id = f"anonymous_{int(time.time())}"
            
            # Verificar cache de respuestas primero
            cache_key = self.cache_service.generate_key(user_id, message)
            cached_response = self.cache_service.get_response(cache_key)
            
            if cached_response:
                response_time = (time.perf_counter() - request_start) * 1000
                logger.info(f"⚡ Respuesta del cache en {response_time:.2f}ms")
                self._update_metrics(response_time)
                return cached_response
            
            # Procesar con el caso de uso
            response = self.procesar_mensaje_use_case.execute(
                mensaje_usuario=message,
                usuario_id=user_id
            )
            
            # Cachear la respuesta
            category = self.cache_service.categorize_message(message)
            self.cache_service.set_response(cache_key, response, category)
            
            # Métricas
            response_time = (time.perf_counter() - request_start) * 1000
            self._update_metrics(response_time)
            
            logger.info(f"✅ Mensaje procesado en {response_time:.2f}ms (total: {self.total_requests})")
            
            return response
            
        except Exception as e:
            response_time = (time.perf_counter() - request_start) * 1000
            logger.error(f"❌ Error procesando mensaje ({response_time:.2f}ms): {e}", exc_info=True)
            return "Lo siento, estoy experimentando problemas técnicos. Por favor, intenta de nuevo."
    
    async def process_message_async(self, user_id: str, message: str) -> str:
        """
        Versión asíncrona del procesamiento de mensajes.
        """
        # Para casos que requieren procesamiento asíncrono
        return await asyncio.get_event_loop().run_in_executor(
            None, self.process_message, user_id, message
        )
    
    def get_performance_stats(self) -> dict:
        """Retorna estadísticas de rendimiento."""
        uptime = time.time() - self.start_time
        avg_response_time = (self.total_response_time / max(self.total_requests, 1)) * 1000
        
        return {
            "uptime_seconds": round(uptime, 2),
            "total_requests": self.total_requests,
            "avg_response_time_ms": round(avg_response_time, 2),
            "requests_per_second": round(self.total_requests / max(uptime, 1), 2),
            "cache_stats": self.cache_service.get_stats(),
            "ai_provider_stats": self.ai_provider.get_cache_stats() if hasattr(self.ai_provider, 'get_cache_stats') else {}
        }
    
    def cleanup_caches(self) -> None:
        """Limpia los caches para liberar memoria."""
        self.cache_service.cleanup_expired()
        if hasattr(self.ai_provider, 'clear_cache'):
            self.ai_provider.clear_cache()
        logger.info("🧹 Caches limpiados")
    
    def _update_metrics(self, response_time_ms: float) -> None:
        """Actualiza métricas internas."""
        self.total_response_time += response_time_ms / 1000  # Convertir a segundos
    
    def health_check(self) -> dict:
        """Verifica el estado de la aplicación."""
        try:
            # Test básico de componentes
            test_response = self.process_message("health_check", "hola")
            
            return {
                "status": "healthy",
                "timestamp": time.time(),
                "components": {
                    "repository": "ok",
                    "ai_provider": "ok",
                    "chatbot_service": "ok",
                    "cache_service": "ok"
                },
                "test_response_length": len(test_response),
                "performance": self.get_performance_stats()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }


# Instancia global de la aplicación
app_instance: Optional[OptimizedChatbotApp] = None


def get_app() -> OptimizedChatbotApp:
    """
    Retorna la instancia global de la aplicación (singleton).
    """
    global app_instance
    if app_instance is None:
        app_instance = OptimizedChatbotApp()
        app_instance.initialize()
    return app_instance


def main():
    """Función principal para ejecutar la aplicación en modo CLI."""
    print("🚀 Iniciando SIACASA Chatbot Optimizado...")
    
    try:
        # Inicializar aplicación
        app = get_app()
        
        # Mostrar estadísticas iniciales
        stats = app.get_performance_stats()
        print(f"✅ Aplicación lista - Tiempo promedio de respuesta: {stats['avg_response_time_ms']:.2f}ms")
        
        # Loop principal de CLI
        print("\n=== SIACASA Chatbot Optimizado ===")
        print("Escribe 'salir' para terminar, 'stats' para ver estadísticas, 'clean' para limpiar cache")
        print("Optimizaciones activas: Cache, Respuestas Rápidas, Timeouts Agresivos\n")
        
        user_id = "cli_user"
        
        while True:
            try:
                user_input = input("\nTú: ").strip()
                
                if user_input.lower() in ['salir', 'exit', 'quit']:
                    print("\n👋 ¡Hasta luego!")
                    break
                
                if user_input.lower() == 'stats':
                    stats = app.get_performance_stats()
                    print(f"\n📊 Estadísticas:")
                    print(f"   Total requests: {stats['total_requests']}")
                    print(f"   Tiempo promedio: {stats['avg_response_time_ms']:.2f}ms")
                    print(f"   Requests/segundo: {stats['requests_per_second']:.2f}")
                    print(f"   Cache hit rate: {stats['cache_stats']['hit_rate_percent']:.1f}%")
                    continue
                
                if user_input.lower() == 'clean':
                    app.cleanup_caches()
                    print("🧹 Caches limpiados")
                    continue
                
                if not user_input:
                    continue
                
                # Procesar mensaje
                start_time = time.perf_counter()
                response = app.process_message(user_id, user_input)
                elapsed = (time.perf_counter() - start_time) * 1000
                
                print(f"\nSIACASA: {response}")
                print(f"⚡ Tiempo de respuesta: {elapsed:.2f}ms")
                
            except KeyboardInterrupt:
                print("\n\n👋 Saliendo...")
                break
            except Exception as e:
                logger.error(f"Error en el loop principal: {e}")
                print(f"❌ Error: {e}")
    
    except Exception as e:
        logger.error(f"Error fatal: {e}", exc_info=True)
        print(f"❌ Error fatal: {e}")


if __name__ == "__main__":
    main()