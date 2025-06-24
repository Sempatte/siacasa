# bot_siacasa/domain/services/response_cache_service.py
import time
import hashlib
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ResponseCacheService:
    """
    Servicio de cache inteligente para respuestas del chatbot.
    Implementa cache con TTL, LRU y categorización de respuestas.
    """

    def __init__(self, max_size: int = 500, default_ttl: int = 3600):
        """
        Inicializa el servicio de cache.
        
        Args:
            max_size: Tamaño máximo del cache
            default_ttl: TTL por defecto en segundos (1 hora)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        
        # Estructuras de cache
        self._cache = {}  # {key: {"response": str, "timestamp": datetime, "ttl": int, "hits": int}}
        self._access_order = []  # Para LRU
        
        # Métricas
        self._hits = 0
        self._misses = 0
        self._total_requests = 0
        
        # Configuración de TTL por categoría
        self.ttl_config = {
            "greeting": 86400,      # Saludos: 24 horas
            "farewell": 86400,      # Despedidas: 24 horas  
            "info_basic": 3600,     # Info básica: 1 hora
            "balance": 300,         # Consultas de saldo: 5 minutos
            "transfer": 60,         # Transferencias: 1 minuto
            "general": 1800,        # General: 30 minutos
            "error": 0              # Errores: sin cache
        }
        
        logger.info(f"ResponseCacheService inicializado - max_size: {max_size}, default_ttl: {default_ttl}s")

    def get_response(self, cache_key: str) -> Optional[str]:
        """
        Obtiene una respuesta del cache.
        
        Args:
            cache_key: Clave del cache
            
        Returns:
            Respuesta si existe y es válida, None en caso contrario
        """
        self._total_requests += 1
        
        if cache_key not in self._cache:
            self._misses += 1
            return None
        
        entry = self._cache[cache_key]
        
        # Verificar TTL
        if self._is_expired(entry):
            self._remove_entry(cache_key)
            self._misses += 1
            return None
        
        # Actualizar orden de acceso (LRU)
        self._update_access_order(cache_key)
        
        # Incrementar hits
        entry["hits"] += 1
        self._hits += 1
        
        logger.debug(f"Cache HIT para key: {cache_key[:20]}...")
        return entry["response"]

    def set_response(self, cache_key: str, response: str, category: str = "general") -> None:
        """
        Almacena una respuesta en el cache.
        
        Args:
            cache_key: Clave del cache
            response: Respuesta a almacenar
            category: Categoría de la respuesta para TTL específico
        """
        # No cachear respuestas de error
        if category == "error" or not response or len(response.strip()) == 0:
            return
        
        ttl = self.ttl_config.get(category, self.default_ttl)
        
        # Crear entrada
        entry = {
            "response": response,
            "timestamp": datetime.now(),
            "ttl": ttl,
            "hits": 0,
            "category": category
        }
        
        # Verificar límite de tamaño
        if len(self._cache) >= self.max_size:
            self._evict_lru()
        
        # Almacenar
        self._cache[cache_key] = entry
        self._update_access_order(cache_key)
        
        logger.debug(f"Cache SET para key: {cache_key[:20]}... (category: {category}, ttl: {ttl}s)")

    def generate_key(self, user_id: str, message: str, context_size: int = 3) -> str:
        """
        Genera una clave de cache basada en el mensaje y contexto.
        
        Args:
            user_id: ID del usuario
            message: Mensaje del usuario
            context_size: Número de palabras de contexto a considerar
            
        Returns:
            Clave de cache
        """
        # Normalizar mensaje
        normalized = message.lower().strip()
        words = normalized.split()
        
        # Usar solo las últimas palabras para generalizar mejor
        context_words = words[-context_size:] if len(words) > context_size else words
        context = " ".join(context_words)
        
        # Generar hash
        cache_string = f"{user_id}_{context}"
        return hashlib.md5(cache_string.encode()).hexdigest()

    def categorize_message(self, message: str) -> str:
        """
        Categoriza un mensaje para aplicar TTL específico.
        
        Args:
            message: Mensaje a categorizar
            
        Returns:
            Categoría del mensaje
        """
        message_lower = message.lower().strip()
        
        # Patrones de categorización
        if any(word in message_lower for word in ["hola", "hi", "buenos", "buenas"]):
            return "greeting"
        
        if any(word in message_lower for word in ["adiós", "chao", "bye", "hasta"]):
            return "farewell"
        
        if any(word in message_lower for word in ["saldo", "balance", "consultar"]):
            return "balance"
        
        if any(word in message_lower for word in ["transferir", "enviar", "transferencia"]):
            return "transfer"
        
        if any(word in message_lower for word in ["horario", "ubicación", "sucursal", "direccion"]):
            return "info_basic"
        
        if any(word in message_lower for word in ["error", "problema", "fallo"]):
            return "error"
        
        return "general"

    def cleanup_expired(self) -> int:
        """
        Limpia entradas expiradas del cache.
        
        Returns:
            Número de entradas eliminadas
        """
        expired_keys = []
        
        for key, entry in self._cache.items():
            if self._is_expired(entry):
                expired_keys.append(key)
        
        for key in expired_keys:
            self._remove_entry(key)
        
        if expired_keys:
            logger.info(f"Cache cleanup: {len(expired_keys)} entradas expiradas eliminadas")
        
        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """
        Retorna estadísticas del cache.
        
        Returns:
            Diccionario con estadísticas
        """
        hit_rate = (self._hits / max(self._total_requests, 1)) * 100
        
        return {
            "total_entries": len(self._cache),
            "max_size": self.max_size,
            "total_requests": self._total_requests,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_percent": round(hit_rate, 2),
            "categories": self._get_category_stats()
        }

    def clear_cache(self) -> None:
        """Limpia completamente el cache."""
        self._cache.clear()
        self._access_order.clear()
        self._hits = 0
        self._misses = 0
        self._total_requests = 0
        logger.info("Cache completamente limpiado")

    def _is_expired(self, entry: Dict) -> bool:
        """Verifica si una entrada ha expirado."""
        if entry["ttl"] == 0:  # TTL 0 = no cachear
            return True
        
        expiry_time = entry["timestamp"] + timedelta(seconds=entry["ttl"])
        return datetime.now() > expiry_time

    def _remove_entry(self, key: str) -> None:
        """Elimina una entrada del cache."""
        if key in self._cache:
            del self._cache[key]
        
        if key in self._access_order:
            self._access_order.remove(key)

    def _update_access_order(self, key: str) -> None:
        """Actualiza el orden de acceso para LRU."""
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

    def _evict_lru(self) -> None:
        """Elimina la entrada menos recientemente usada."""
        if self._access_order:
            lru_key = self._access_order[0]
            self._remove_entry(lru_key)
            logger.debug(f"Cache LRU eviction: {lru_key[:20]}...")

    def _get_category_stats(self) -> Dict[str, int]:
        """Retorna estadísticas por categoría."""
        stats = {}
        for entry in self._cache.values():
            category = entry.get("category", "unknown")
            stats[category] = stats.get(category, 0) + 1
        return stats


# Instancia global del cache (singleton pattern)
_cache_instance = None

def get_cache_service() -> ResponseCacheService:
    """
    Retorna la instancia global del servicio de cache.
    
    Returns:
        Instancia del ResponseCacheService
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = ResponseCacheService()
    return _cache_instance