# bot_siacasa/config/config.py
import os
from typing import Dict, Any
from dotenv import load_dotenv
load_dotenv()
class OptimizedConfig:
    """
    Configuración optimizada para máximo rendimiento del chatbot.
    """
    
    # === CONFIGURACIÓN DE OPENAI OPTIMIZADA ===
    OPENAI_CONFIG = {
        "model": "gpt-3.5-turbo",      # Modelo más rápido
        "max_tokens": 300,           # Respuestas más cortas = más rápidas
        "temperature": 0.3,          # Menos variabilidad = más consistente y rápido
        "top_p": 0.9,               # Reduce opciones = más rápido
        "presence_penalty": 0,       # Sin penalización = más rápido
        "frequency_penalty": 0,      # Sin penalización = más rápido
        "timeout": 8.0,             # Timeout agresivo de 8 segundos
        "max_retries": 1            # Solo 1 retry para no demorar
    }
    
    # === CONFIGURACIÓN DE CACHE ===
    CACHE_CONFIG = {
        "response_cache_size": 500,     # Cache de respuestas
        "sentiment_cache_size": 200,    # Cache de análisis de sentimiento
        "conversation_cache_size": 100, # Cache de conversaciones
        "response_ttl": 3600,          # TTL de 1 hora para respuestas
        "sentiment_ttl": 7200,         # TTL de 2 horas para sentimientos
        "enable_cache": True
    }
    
    # === CONFIGURACIÓN DE HISTORIAL OPTIMIZADA ===
    CONVERSATION_CONFIG = {
        "max_messages_in_history": 15,    # Máximo 15 mensajes en historial
        "max_messages_to_ai": 10,         # Máximo 10 mensajes a la IA
        "context_window_size": 8,         # Ventana de contexto de 8 mensajes
        "enable_conversation_compression": True
    }
    
    # === TIMEOUTS AGRESIVOS ===
    TIMEOUT_CONFIG = {
        "ai_response_timeout": 8.0,       # 8 segundos para respuesta de IA
        "db_query_timeout": 2.0,          # 2 segundos para consultas DB
        "cache_operation_timeout": 0.5,   # 0.5 segundos para operaciones de cache
        "sentiment_analysis_timeout": 3.0, # 3 segundos para análisis de sentimiento
        "escalation_check_timeout": 1.0   # 1 segundo para verificar escalación
    }
    
    # === CONFIGURACIÓN DE RESPUESTAS RÁPIDAS ===
    QUICK_RESPONSES = {
        "enable_quick_responses": True,
        "response_patterns": {
            r"(?i)(hola|hi|buenos días|buenas tardes|buenas noches)": "¡Hola! Soy SIACASA, tu asistente bancario virtual. ¿En qué puedo ayudarte hoy?",
            r"(?i)(gracias|muchas gracias|thank you)": "¡De nada! ¿Hay algo más en lo que pueda ayudarte?",
            r"(?i)(adiós|chao|hasta luego|bye)": "¡Hasta luego! Que tengas un excelente día.",
            r"(?i)(mi saldo|saldo actual|consultar saldo)": "Para consultar tu saldo necesito verificar tu identidad. ¿Podrías proporcionarme tu número de cuenta?",
            r"(?i)(transferir dinero|hacer transferencia)": "Te ayudo con tu transferencia. ¿A qué cuenta deseas transferir y por qué monto?",
            r"(?i)(horarios|horario de atención)": "Nuestro horario de atención es de lunes a viernes de 9:00 AM a 6:00 PM, y sábados de 9:00 AM a 1:00 PM.",
            r"(?i)(ubicaciones|sucursales|donde están)": "Tenemos sucursales en todo el país. ¿En qué ciudad te gustaría encontrar una sucursal?"
        }
    }
    
    # === CONFIGURACIÓN DE LOGGING OPTIMIZADA ===
    LOGGING_CONFIG = {
        "level": "INFO",
        "enable_performance_logging": True,
        "log_response_times": True,
        "log_cache_hits": False,  # Solo en debug
        "max_log_message_length": 100
    }
    
    # === CONFIGURACIÓN DE BASE DE DATOS OPTIMIZADA ===
    DATABASE_CONFIG = {
        "connection_pool_size": 10,
        "max_overflow": 20,
        "pool_timeout": 2.0,
        "pool_recycle": 3600,
        "enable_query_caching": True,
        "query_cache_size": 1000
    }
    
    # === CONFIGURACIÓN DE ANÁLISIS DE SENTIMIENTO ===
    SENTIMENT_CONFIG = {
        "enable_sentiment_analysis": True,
        "use_cache": True,
        "timeout": 3.0,
        "fallback_sentiment": "neutral",
        "batch_analysis": False  # Análisis individual para velocidad
    }
    
    # === CONFIGURACIÓN DE ESCALACIÓN ===
    ESCALATION_CONFIG = {
        "enable_escalation": True,
        "escalation_keywords": [
            "hablar con humano", "hablar con persona", "hablar con agente",
            "atención humana", "necesito un agente", "comunicarme con un humano",
            "no entiendes", "no me ayudas", "transferir a agente"
        ],
        "max_failed_attempts": 3,
        "escalation_timeout": 1.0
    }
    
    # === CONFIGURACIÓN DE MÉTRICAS ===
    METRICS_CONFIG = {
        "enable_metrics": True,
        "enable_detailed_metrics": False,  # Solo métricas básicas para velocidad
        "metrics_buffer_size": 100,
        "flush_interval": 300  # 5 minutos
    }
    
    # === CONFIGURACIÓN DE RENDIMIENTO ===
    PERFORMANCE_CONFIG = {
        "enable_async_processing": True,
        "max_concurrent_requests": 10,
        "request_timeout": 30.0,
        "enable_request_batching": False,  # Individual para menor latencia
        "memory_limit_mb": 512,
        "gc_threshold": 1000  # Garbage collection cada 1000 requests
    }
    
    # === CONFIGURACIÓN DE SEGURIDAD ===
    SECURITY_CONFIG = {
        "rate_limit_per_minute": 60,
        "max_message_length": 1000,
        "enable_input_sanitization": True,
        "log_security_events": True,
        "block_suspicious_patterns": True
    }
    
    # === CONFIGURACIÓN DE MONITOREO ===
    MONITORING_CONFIG = {
        "enable_health_checks": True,
        "health_check_interval": 60,  # segundos
        "enable_performance_alerts": True,
        "slow_response_threshold_ms": 10000,  # 10 segundos
        "error_rate_threshold_percent": 5.0
    }
    
    @classmethod
    def get_all_config(cls) -> Dict[str, Any]:
        """Retorna toda la configuración como un diccionario."""
        return {
            "openai": cls.OPENAI_CONFIG,
            "cache": cls.CACHE_CONFIG,
            "conversation": cls.CONVERSATION_CONFIG,
            "timeouts": cls.TIMEOUT_CONFIG,
            "quick_responses": cls.QUICK_RESPONSES,
            "logging": cls.LOGGING_CONFIG,
            "database": cls.DATABASE_CONFIG,
            "sentiment": cls.SENTIMENT_CONFIG,
            "escalation": cls.ESCALATION_CONFIG,
            "metrics": cls.METRICS_CONFIG,
            "performance": cls.PERFORMANCE_CONFIG,
            "security": cls.SECURITY_CONFIG,
            "monitoring": cls.MONITORING_CONFIG
        }
    
    @classmethod
    def get_openai_config(cls) -> Dict[str, Any]:
        """Retorna solo la configuración de OpenAI."""
        return cls.OPENAI_CONFIG.copy()
    
    @classmethod
    def get_performance_config(cls) -> Dict[str, Any]:
        """Retorna configuración enfocada en rendimiento."""
        return {
            "ai_timeout": cls.TIMEOUT_CONFIG["ai_response_timeout"],
            "max_history": cls.CONVERSATION_CONFIG["max_messages_to_ai"],
            "cache_enabled": cls.CACHE_CONFIG["enable_cache"],
            "quick_responses": cls.QUICK_RESPONSES["enable_quick_responses"],
            "model": cls.OPENAI_CONFIG["model"],
            "max_tokens": cls.OPENAI_CONFIG["max_tokens"],
            "max_concurrent": cls.PERFORMANCE_CONFIG["max_concurrent_requests"]
        }
    
    @classmethod
    def get_cache_config(cls) -> Dict[str, Any]:
        """Retorna configuración de cache."""
        return cls.CACHE_CONFIG.copy()
    
    @classmethod
    def get_timeout_config(cls) -> Dict[str, Any]:
        """Retorna configuración de timeouts."""
        return cls.TIMEOUT_CONFIG.copy()


# === VARIABLES DE ENTORNO ===
class EnvironmentConfig:
    """Configuración basada en variables de entorno."""
    
    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    
    # Configuración del servidor
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "3200"))
    BANK_CODE = os.getenv("BANK_CODE", "default")
    
    # Base de datos
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///chatbot.db")
    
    # Configuración de entorno
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    # Configuración de cache
    REDIS_URL = os.getenv("REDIS_URL", None)
    ENABLE_REDIS_CACHE = REDIS_URL is not None
    
    # Configuración de logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    ENABLE_FILE_LOGGING = os.getenv("ENABLE_FILE_LOGGING", "False").lower() == "true"
    LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "logs/chatbot.log")
    
    # Límites de rendimiento
    MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "10"))
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

    # Configuración de repositorio/NeonDB
    NEONDB_CONNECT_TIMEOUT = int(os.getenv("NEONDB_CONNECT_TIMEOUT", "5"))
    USE_MEMORY_REPOSITORY = os.getenv("USE_MEMORY_REPOSITORY", "False").lower() == "true"
    DISABLE_NEONDB = os.getenv("DISABLE_NEONDB", "False").lower() == "true"
    
    # Configuración de OpenAI
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "300"))
    OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
    OPENAI_TIMEOUT = float(os.getenv("OPENAI_TIMEOUT", "8.0"))
    
    # Configuración de cache
    CACHE_SIZE = int(os.getenv("CACHE_SIZE", "500"))
    CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))
    
    # Seguridad
    ENABLE_RATE_LIMITING = os.getenv("ENABLE_RATE_LIMITING", "True").lower() == "true"
    MAX_MESSAGE_LENGTH = int(os.getenv("MAX_MESSAGE_LENGTH", "1000"))
    
    @classmethod
    def is_production(cls) -> bool:
        """Verifica si está en entorno de producción."""
        return cls.ENVIRONMENT.lower() == "production"
    
    @classmethod
    def is_development(cls) -> bool:
        """Verifica si está en entorno de desarrollo."""
        return cls.ENVIRONMENT.lower() == "development"
    
    @classmethod
    def get_database_config(cls) -> Dict[str, Any]:
        """Retorna configuración de base de datos según entorno."""
        base_config = OptimizedConfig.DATABASE_CONFIG.copy()
        
        if cls.is_production():
            base_config.update({
                "connection_pool_size": 20,
                "max_overflow": 50,
                "pool_timeout": 5.0
            })
        
        return base_config
    
    @classmethod
    def get_openai_config_from_env(cls) -> Dict[str, Any]:
        """Retorna configuración de OpenAI desde variables de entorno."""
        return {
            "model": cls.OPENAI_MODEL,
            "max_tokens": cls.OPENAI_MAX_TOKENS,
            "temperature": cls.OPENAI_TEMPERATURE,
            "timeout": cls.OPENAI_TIMEOUT,
            "api_key": cls.OPENAI_API_KEY
        }
    
    @classmethod
    def validate_config(cls) -> Dict[str, Any]:
        """Valida la configuración y retorna errores si los hay."""
        errors = []
        warnings = []
        
        # Validar API Key
        if not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY no está configurada")
        elif not cls.OPENAI_API_KEY.startswith("sk-"):
            warnings.append("OPENAI_API_KEY no tiene el formato esperado")
        
        # Validar timeouts
        if cls.OPENAI_TIMEOUT < 1.0:
            warnings.append("OPENAI_TIMEOUT muy bajo, puede causar errores")
        elif cls.OPENAI_TIMEOUT > 30.0:
            warnings.append("OPENAI_TIMEOUT muy alto, puede afectar UX")
        
        # Validar límites
        if cls.MAX_CONCURRENT_REQUESTS > 50:
            warnings.append("MAX_CONCURRENT_REQUESTS muy alto")
        
        if cls.CACHE_SIZE > 10000:
            warnings.append("CACHE_SIZE muy alto, puede consumir mucha memoria")
        
        return {
            "errors": errors,
            "warnings": warnings,
            "is_valid": len(errors) == 0
        }


# === CONFIGURACIÓN GLOBAL ===
def get_optimized_config() -> Dict[str, Any]:
    """
    Retorna la configuración completa optimizada para el entorno actual.
    """
    config = OptimizedConfig.get_all_config()
    env_config = EnvironmentConfig
    
    # Sobrescribir con variables de entorno si están disponibles
    config["openai"].update(env_config.get_openai_config_from_env())
    
    # Ajustar configuración según entorno
    if env_config.is_production():
        config["openai"]["timeout"] = 12.0  # Más tiempo en producción
        config["cache"]["response_cache_size"] = 1000  # Cache más grande
        config["logging"]["level"] = "WARNING"  # Menos logs en producción
        config["performance"]["max_concurrent_requests"] = 20
    elif env_config.DEBUG:
        config["logging"]["level"] = "DEBUG"
        config["logging"]["log_cache_hits"] = True
        config["openai"]["timeout"] = 15.0  # Más tiempo para debug
    
    return config


def get_config_for_environment(environment: str) -> Dict[str, Any]:
    """
    Retorna configuración específica para un entorno.
    
    Args:
        environment: 'development', 'production', 'testing'
    """
    config = OptimizedConfig.get_all_config()
    
    if environment == "production":
        config.update({
            "openai": {**config["openai"], "timeout": 12.0, "max_retries": 2},
            "cache": {**config["cache"], "response_cache_size": 2000},
            "logging": {**config["logging"], "level": "WARNING"},
            "performance": {**config["performance"], "max_concurrent_requests": 25}
        })
    elif environment == "testing":
        config.update({
            "openai": {**config["openai"], "model": "gpt-3.5-turbo", "timeout": 5.0},
            "cache": {**config["cache"], "enable_cache": False},
            "logging": {**config["logging"], "level": "ERROR"}
        })
    elif environment == "development":
        config.update({
            "logging": {**config["logging"], "level": "DEBUG", "log_cache_hits": True},
            "openai": {**config["openai"], "timeout": 15.0}
        })
    
    return config


# === CONSTANTES DE RENDIMIENTO ===
class PerformanceConstants:
    """Constantes optimizadas para rendimiento."""
    
    # Límites de tokens
    MAX_INPUT_TOKENS = 3000
    MAX_OUTPUT_TOKENS = 300
    MAX_TOTAL_TOKENS = 3300
    
    # Límites de mensajes
    MAX_MESSAGE_LENGTH = 1000
    MAX_MESSAGES_PER_CONVERSATION = 50
    MAX_CONVERSATIONS_PER_USER = 5
    
    # Límites de tiempo
    MAX_RESPONSE_TIME_MS = 8000
    MAX_DB_QUERY_TIME_MS = 2000
    MAX_CACHE_OPERATION_TIME_MS = 500
    
    # Límites de cache
    MAX_CACHE_KEY_LENGTH = 256
    MAX_CACHE_VALUE_SIZE_KB = 10
    MAX_CACHE_ENTRIES = 10000
    
    # Frecuencias de limpieza
    CACHE_CLEANUP_INTERVAL_SECONDS = 300  # 5 minutos
    METRICS_FLUSH_INTERVAL_SECONDS = 60   # 1 minuto
    LOG_ROTATION_INTERVAL_HOURS = 24      # 24 horas
    
    # Thresholds de alerta
    SLOW_RESPONSE_THRESHOLD_MS = 10000    # 10 segundos
    HIGH_ERROR_RATE_THRESHOLD = 0.1       # 10%
    HIGH_MEMORY_USAGE_THRESHOLD_MB = 1024 # 1GB


# === CONFIGURACIÓN DE DESARROLLO ===
class DevelopmentConfig(OptimizedConfig):
    """Configuración específica para desarrollo."""
    
    OPENAI_CONFIG = {
        **OptimizedConfig.OPENAI_CONFIG,
        "timeout": 15.0,  # Más tiempo para debug
        "temperature": 0.7  # Más creatividad para pruebas
    }
    
    LOGGING_CONFIG = {
        **OptimizedConfig.LOGGING_CONFIG,
        "level": "DEBUG",
        "log_cache_hits": True,
        "enable_performance_logging": True
    }
    
    CACHE_CONFIG = {
        **OptimizedConfig.CACHE_CONFIG,
        "response_cache_size": 100  # Cache más pequeño para desarrollo
    }


# === CONFIGURACIÓN DE PRODUCCIÓN ===
class ProductionConfig(OptimizedConfig):
    """Configuración específica para producción."""
    
    OPENAI_CONFIG = {
        **OptimizedConfig.OPENAI_CONFIG,
        "timeout": 10.0,  # Timeout más generoso en producción
        "max_retries": 2  # Más reintentos en producción
    }
    
    LOGGING_CONFIG = {
        **OptimizedConfig.LOGGING_CONFIG,
        "level": "WARNING",
        "log_cache_hits": False,
        "max_log_message_length": 50  # Logs más cortos
    }
    
    CACHE_CONFIG = {
        **OptimizedConfig.CACHE_CONFIG,
        "response_cache_size": 2000,  # Cache más grande en producción
        "sentiment_cache_size": 500
    }
    
    PERFORMANCE_CONFIG = {
        **OptimizedConfig.PERFORMANCE_CONFIG,
        "max_concurrent_requests": 25,  # Más concurrencia en producción
        "memory_limit_mb": 2048  # Más memoria disponible
    }


# Función helper para obtener configuración según entorno
def get_config_class():
    """Retorna la clase de configuración según el entorno."""
    env = EnvironmentConfig.ENVIRONMENT.lower()
    
    if env == "production":
        return ProductionConfig
    elif env == "development":
        return DevelopmentConfig
    else:
        return OptimizedConfig
