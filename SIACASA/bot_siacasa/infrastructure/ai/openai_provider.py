# bot_siacasa/infrastructure/ai/openai_provider.py
from datetime import datetime
import json
import logging
import time
import hashlib
from typing import Dict, List, Optional
import openai
import asyncio
import aiohttp

from bot_siacasa.application.interfaces.ia_provider_interface import IAProviderInterface

logger = logging.getLogger(__name__)

class OpenAIProvider(IAProviderInterface):
    """
    Implementación optimizada del proveedor de IA utilizando la API de OpenAI.
    Incluye cache, timeouts y configuración optimizada para velocidad.
    """
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        """
        Inicializa el proveedor de OpenAI optimizado.
        
        Args:
            api_key: API key de OpenAI
            model: Modelo de OpenAI a utilizar (por defecto gpt-3.5-turbo para velocidad)
        """
        self.model = model
        self.api_key = api_key
        openai.api_key = api_key
        
        # Cache para respuestas de IA
        self._response_cache = {}
        self._sentiment_cache = {}
        self._max_cache_size = 200
        
        # Configuración optimizada para velocidad
        self.config_optimized = {
            "max_tokens": 300,        # Respuestas más cortas = más rápidas
            "temperature": 0.3,       # Menos variabilidad = más rápido
            "top_p": 0.9,            # Reduce opciones = más rápido
            "presence_penalty": 0,    # Sin penalización = más rápido
            "frequency_penalty": 0,   # Sin penalización = más rápido
            "timeout": 8.0           # Timeout agresivo
        }
        
        # Headers para requests async
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"OpenAI Provider inicializado con modelo {model} - Configuración optimizada para velocidad")
    
    def _generate_cache_key(self, messages: List[Dict], extra: str = "") -> str:
        """Genera clave de cache basada en los mensajes"""
        # Usar solo los últimos 3 mensajes para cache más efectivo
        recent_messages = messages[-3:] if len(messages) > 3 else messages
        content = ""
        for msg in recent_messages:
            content += f"{msg.get('role', '')}:{msg.get('content', '')}"
        
        cache_string = content + extra
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def _add_to_cache(self, cache_dict: dict, key: str, value):
        """Agrega elemento al cache con límite de tamaño"""
        if len(cache_dict) >= self._max_cache_size:
            # Remover el más antiguo (FIFO)
            oldest_key = next(iter(cache_dict))
            del cache_dict[oldest_key]
        
        cache_dict[key] = value
    
    def analizar_sentimiento(self, texto: str) -> Dict:
        """
        Analiza el sentimiento del texto de manera más completa.
        """
        start_time = time.perf_counter()
        
        try:
            # Verificar cache primero
            cache_key = hashlib.md5(texto.strip().lower().encode()).hexdigest()
            if cache_key in self._sentiment_cache:
                execution_time = (time.perf_counter() - start_time) * 1000
                logger.debug(f"Sentimiento obtenido del cache en {execution_time:.2f}ms")
                return self._sentiment_cache[cache_key]
            
            # Prompt mejorado para análisis completo
            system_prompt = """Analiza el siguiente texto y responde SOLO con JSON válido con esta estructura exacta:
    {
        "sentimiento": "positivo/negativo/neutral",
        "confianza": 0.0-1.0,
        "emociones": ["lista de emociones detectadas"],
        "intent": "tipo de intención del usuario",
        "intent_confidence": 0.0-1.0,
        "entidades": {
            "monto": "si menciona cantidad de dinero",
            "producto": "si menciona producto bancario",
            "accion": "acción que desea realizar"
        },
        "escalacion_requerida": true/false,
        "tono_sugerido": "tono recomendado para responder"
    }

    Contexto: Eres un analizador para un chatbot bancario. Los intents comunes son:
    - consulta_saldo: preguntas sobre saldo o estado de cuenta
    - transferencia: desea transferir dinero
    - prestamo: consultas sobre préstamos o créditos
    - tarjeta: consultas sobre tarjetas
    - soporte: problemas o quejas
    - saludo: saludos o despedidas
    - consulta_general: otras consultas

    Las emociones pueden ser: felicidad, tristeza, enojo, frustración, confusión, satisfacción, neutral.
    Los tonos sugeridos: profesional, empático, amigable, formal, tranquilizador."""

            # Hacer la llamada a OpenAI
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analiza este texto: \"{texto}\""}
                ],
                response_format={"type": "json_object"},
                max_tokens=200,  # Un poco más para el análisis completo
                temperature=0.1,  # Muy determinístico
                timeout=5.0
            )
            
            # Procesar resultado
            resultado_json = json.loads(response.choices[0].message.content)
            
            # Normalizar y validar el resultado
            resultado_normalizado = {
                "sentimiento": resultado_json.get("sentimiento", "neutral"),
                "confianza": float(resultado_json.get("confianza", 0.5)),
                "emociones": resultado_json.get("emociones", []),
                "intent": resultado_json.get("intent", "consulta_general"),
                "intent_confidence": float(resultado_json.get("intent_confidence", 0.7)),
                "entidades": resultado_json.get("entidades", {}),
                "escalacion_requerida": resultado_json.get("escalacion_requerida", False),
                "tono_sugerido": resultado_json.get("tono_sugerido", "profesional"),
                "metadata": {
                    "analyzed_at": datetime.now().isoformat(),
                    "model": self.model
                }
            }
            
            # Agregar al cache
            self._add_to_cache(self._sentiment_cache, cache_key, resultado_normalizado)
            
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.debug(f"Sentimiento analizado con IA en {execution_time:.2f}ms")
            
            return resultado_normalizado
            
        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.error(f"Error en análisis de sentimiento ({execution_time:.2f}ms): {e}")
            
            # Fallback mejorado con análisis básico por reglas
            return self._analisis_fallback(texto)
    def generar_respuesta(self, mensajes: List[Dict[str, str]], instrucciones_adicionales: str = None) -> str:
        """
        Genera respuesta optimizada con cache y configuración de velocidad.
        """
        start_time = time.perf_counter()
        
        try:
            # 1. Verificar cache primero
            cache_key = self._generate_cache_key(mensajes, instrucciones_adicionales or "")
            if cache_key in self._response_cache:
                execution_time = (time.perf_counter() - start_time) * 1000
                logger.debug(f"Respuesta obtenida del cache en {execution_time:.2f}ms")
                return self._response_cache[cache_key]
            
            # 2. Validar y preparar mensajes
            mensajes_validados = self._validar_mensajes(mensajes)
            
            # 3. Agregar instrucciones adicionales si las hay
            if instrucciones_adicionales:
                mensajes_validados = self._agregar_instrucciones(mensajes_validados, instrucciones_adicionales)
            
            # 4. Log de contexto (solo primeros mensajes)
            logger.info(f"Enviando {len(mensajes_validados)} mensajes a OpenAI (modelo: {self.model})")
            for i, msg in enumerate(mensajes_validados[:2]):  # Solo primeros 2 para el log
                role = msg['role']
                content_preview = msg['content'][:40] + "..." if len(msg['content']) > 40 else msg['content']
                logger.debug(f"  Mensaje #{i}: {role} - {content_preview}")
            
            # 5. Llamada a OpenAI con configuración optimizada
            
            # Preparamos los argumentos para la llamada a la API.
            # Quitamos 'model' porque se pasa explícitamente y otros params no válidos.
            api_params = self.config_optimized.copy()
            api_params.pop('model', None)
            api_params.pop('max_retries', None)
            api_params.pop('api_key', None)

            response = openai.chat.completions.create(
                model=self.model,
                messages=mensajes_validados,
                **api_params  # Usar configuración optimizada y limpia
            )
            
            # 6. Extraer respuesta
            respuesta = response.choices[0].message.content
            
            # 7. Agregar al cache
            self._add_to_cache(self._response_cache, cache_key, respuesta)
            
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.info(f"✅ Respuesta OpenAI generada en {execution_time:.2f}ms")
            
            return respuesta
            
        except openai.APITimeoutError as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.error(f"Timeout en OpenAI ({execution_time:.2f}ms): {e}")
            return "Disculpa, mi respuesta está tardando más de lo esperado. ¿Podrías reformular tu pregunta?"
            
        except openai.RateLimitError as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.error(f"Rate limit en OpenAI ({execution_time:.2f}ms): {e}")
            return "Estoy recibiendo muchas consultas en este momento. Por favor, intenta de nuevo en unos segundos."
            
        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.error(f"Error generando respuesta ({execution_time:.2f}ms): {e}", exc_info=True)
            return "Lo siento, estoy experimentando problemas técnicos en este momento. ¿Podrías intentarlo de nuevo más tarde?"
    
    def _validar_mensajes(self, mensajes: List[Dict]) -> List[Dict]:
        """Valida y limpia los mensajes de entrada"""
        mensajes_validados = []
        
        for msg in mensajes:
            if not isinstance(msg, dict) or 'role' not in msg or 'content' not in msg:
                logger.warning(f"Mensaje con formato incorrecto ignorado: {msg}")
                continue
            
            # Validar rol
            if msg['role'] not in ["system", "user", "assistant"]:
                logger.warning(f"Mensaje con rol inválido ignorado: {msg['role']}")
                continue
            
            # Limpiar contenido
            content = str(msg['content']).strip()
            if not content:
                logger.warning("Mensaje con contenido vacío ignorado")
                continue
            
            mensajes_validados.append({
                "role": msg['role'],
                "content": content
            })
        
        # Si no hay mensajes válidos, crear uno básico
        if not mensajes_validados:
            logger.warning("No hay mensajes válidos, usando mensaje de sistema por defecto")
            mensajes_validados = [{
                "role": "system",
                "content": "Eres SIACASA, un asistente bancario virtual. Ayuda al usuario de forma clara y concisa."
            }]
        
        return mensajes_validados
    
    def _agregar_instrucciones(self, mensajes: List[Dict], instrucciones: str) -> List[Dict]:
        """Agrega instrucciones adicionales al mensaje de sistema"""
        # Buscar mensaje de sistema existente
        for msg in mensajes:
            if msg['role'] == 'system':
                # Actualizar el contenido del mensaje de sistema
                msg['content'] += f"\n\nInstrucciones adicionales: {instrucciones}"
                return mensajes
        
        # Si no hay mensaje de sistema, agregar uno nuevo al inicio
        mensajes.insert(0, {
            "role": "system",
            "content": f"Eres SIACASA, un asistente bancario virtual.\n\nInstrucciones adicionales: {instrucciones}"
        })
        
        return mensajes
    
    async def generar_respuesta_async(self, mensajes: List[Dict[str, str]], instrucciones_adicionales: str = None) -> str:
        """
        Versión asíncrona de generar_respuesta para casos que requieren paralelización.
        """
        start_time = time.perf_counter()
        
        try:
            # Verificar cache
            cache_key = self._generate_cache_key(mensajes, instrucciones_adicionales or "")
            if cache_key in self._response_cache:
                return self._response_cache[cache_key]
            
            # Preparar mensajes
            mensajes_validados = self._validar_mensajes(mensajes)
            if instrucciones_adicionales:
                mensajes_validados = self._agregar_instrucciones(mensajes_validados, instrucciones_adicionales)
            
            # Hacer request asíncrono
            payload = {
                "model": self.model,
                "messages": mensajes_validados,
                **self.config_optimized
            }
            
            timeout = aiohttp.ClientTimeout(total=self.config_optimized["timeout"])
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    json=payload,
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        respuesta = data['choices'][0]['message']['content']
                        
                        # Agregar al cache
                        self._add_to_cache(self._response_cache, cache_key, respuesta)
                        
                        execution_time = (time.perf_counter() - start_time) * 1000
                        logger.info(f"✅ Respuesta async OpenAI en {execution_time:.2f}ms")
                        
                        return respuesta
                    else:
                        error_text = await response.text()
                        raise Exception(f"OpenAI API error {response.status}: {error_text}")
            
        except asyncio.TimeoutError:
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.error(f"Timeout async en OpenAI ({execution_time:.2f}ms)")
            return "Disculpa, mi respuesta está tardando más de lo esperado. ¿Podrías reformular tu pregunta?"
        
        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.error(f"Error async generando respuesta ({execution_time:.2f}ms): {e}")
            return "Lo siento, estoy experimentando problemas técnicos. ¿Podrías intentarlo de nuevo?"
    
    async def generar_respuesta_stream(self, mensajes: List[Dict[str, str]]) -> str:
        """
        Genera respuesta con streaming para mostrar progreso (futuro).
        Por ahora retorna respuesta normal.
        """
        return await self.generar_respuesta_async(mensajes)
    
    def get_cache_stats(self) -> Dict:
        """Retorna estadísticas del cache para monitoreo"""
        total_response_requests = getattr(self, '_response_requests', 0)
        total_sentiment_requests = getattr(self, '_sentiment_requests', 0)
        response_hits = getattr(self, '_response_hits', 0)
        sentiment_hits = getattr(self, '_sentiment_hits', 0)
        
        return {
            "response_cache_size": len(self._response_cache),
            "sentiment_cache_size": len(self._sentiment_cache),
            "max_cache_size": self._max_cache_size,
            "response_cache_hit_rate": response_hits / max(total_response_requests, 1),
            "sentiment_cache_hit_rate": sentiment_hits / max(total_sentiment_requests, 1),
            "total_response_requests": total_response_requests,
            "total_sentiment_requests": total_sentiment_requests,
            "response_hits": response_hits,
            "sentiment_hits": sentiment_hits
        }
    
    def clear_cache(self):
        """Limpia todos los caches"""
        self._response_cache.clear()
        self._sentiment_cache.clear()
        # Reset métricas
        self._response_hits = 0
        self._response_requests = 0
        self._sentiment_hits = 0
        self._sentiment_requests = 0
        logger.info("Cache de OpenAI Provider limpiado")
    
    def set_model(self, model: str):
        """Cambia el modelo de OpenAI"""
        old_model = self.model
        self.model = model
        # Limpiar cache al cambiar modelo
        self.clear_cache()
        logger.info(f"Modelo cambiado de {old_model} a {model}")
    
    def update_config(self, **kwargs):
        """Actualiza la configuración del provider"""
        old_config = self.config_optimized.copy()
        self.config_optimized.update(kwargs)
        logger.info(f"Configuración actualizada de {old_config} a {self.config_optimized}")
    
    def get_model_info(self) -> Dict:
        """Retorna información del modelo actual"""
        return {
            "model": self.model,
            "config": self.config_optimized.copy(),
            "cache_stats": self.get_cache_stats()
        }
    
    def test_connection(self) -> bool:
        """Prueba la conexión con OpenAI"""
        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
                timeout=5.0
            )
            return True
        except Exception as e:
            logger.error(f"Error probando conexión OpenAI: {e}")
            return False
    
    def get_token_estimate(self, text: str) -> int:
        """Estima el número de tokens de un texto"""
        # Estimación básica: ~1.3 tokens por palabra
        words = len(text.split())
        return int(words * 1.3)
    
    def optimize_messages_for_speed(self, messages: List[Dict]) -> List[Dict]:
        """Optimiza mensajes para máxima velocidad"""
        # Limitar a últimos N mensajes
        max_messages = 8
        
        if len(messages) <= max_messages:
            return messages
        
        # Mantener mensaje de sistema + últimos mensajes
        system_msgs = [m for m in messages if m.get('role') == 'system']
        other_msgs = [m for m in messages if m.get('role') != 'system']
        
        # Tomar los más recientes
        recent_msgs = other_msgs[-(max_messages - len(system_msgs)):]
        
        optimized = system_msgs + recent_msgs
        logger.debug(f"Mensajes optimizados: {len(messages)} -> {len(optimized)}")
        
        return optimized