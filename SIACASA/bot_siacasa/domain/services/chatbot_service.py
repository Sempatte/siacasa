# bot_siacasa/domain/services/chatbot_service.py
import uuid
import logging
import time
import re
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, TYPE_CHECKING

from bot_siacasa.domain.entities.mensaje import Mensaje
from bot_siacasa.domain.entities.usuario import Usuario
from bot_siacasa.domain.entities.conversacion import Conversacion
from bot_siacasa.domain.entities.analisis_sentimiento import AnalisisSentimiento
from bot_siacasa.domain.entities.ticket import Ticket, TicketStatus, EscalationReason
from bot_siacasa.application.interfaces.repository_interface import IRepository
from bot_siacasa.domain.services.escalation_service import EscalationService

# Evitar importación circular
if TYPE_CHECKING:
    from bot_siacasa.application.use_cases.analizar_sentimiento_use_case import (
        AnalizarSentimientoUseCase,
    )

logger = logging.getLogger(__name__)


class ChatbotService:
    """
    Servicio principal del chatbot que implementa la lógica de negocio.
    VERSIÓN OPTIMIZADA con cache, respuestas rápidas y medición de tiempo.
    """

    # Respuestas instantáneas para casos comunes
    RESPUESTAS_RAPIDAS = {
        r"(?i)(hola|hi|buenos días|buenas tardes|buenas noches|saludos)": "¡Hola! Soy SIACASA, tu asistente bancario virtual. ¿En qué puedo ayudarte hoy?",
        r"(?i)(gracias|muchas gracias|thank you|thanks)": "¡De nada! ¿Hay algo más en lo que pueda ayudarte?",
        r"(?i)(adiós|chao|hasta luego|bye|goodbye)": "¡Hasta luego! Que tengas un excelente día. Recuerda que estoy aquí cuando me necesites.",
        r"(?i)(mi saldo|saldo actual|consultar saldo|ver mi saldo)": "Para consultar tu saldo necesito verificar tu identidad. ¿Podrías proporcionarme tu número de cuenta o DNI?"
    }

    def __init__(
        self, repository: IRepository, sentimiento_analyzer, ai_provider=None, bank_config=None,
        support_repository=None
    ):
        """
        Inicializa el servicio del chatbot.
        """
        self.repository = repository
        self.sentimiento_analyzer = sentimiento_analyzer
        self.ai_provider = ai_provider
        self.support_repository = support_repository

        # Cache para optimizar rendimiento
        self._sentiment_cache = {}
        self._conversation_cache = {}
        self._response_cache = {}
        self._max_cache_size = 100

        default_config = {
            "bank_name": "Banco",
            "greeting": "Hola, soy SIACASA, tu asistente bancario virtual.",
            "style": "formal"
        }

        self.escalation_service = None
        if support_repository:
            self.escalation_service = EscalationService(support_repository)
            logger.info("Escalation service initialized successfully")
        else:
            logger.warning(
                "Support repository not provided, escalation service not initialized")

        self.bank_config = {**default_config, **(bank_config or {})}

        # Mensaje de sistema optimizado
        self.mensaje_sistema = Mensaje(
            role="system",
            content=f"""Eres SIACASA, un asistente bancario virtual del {self.bank_config['bank_name']}. 
            
Características:
- Responde de forma clara, concisa y profesional
- Ayuda con consultas de saldo, transferencias, productos bancarios y dudas generales
- Si no puedes resolver algo, ofrece escalación a un agente humano
- Mantén el contexto de la conversación
- No repitas saludos en cada respuesta
- Usa lenguaje sencillo y evita jerga técnica"""
        )

    def obtener_respuesta_rapida(self, texto: str) -> Optional[str]:
        """
        Verifica si hay una respuesta rápida disponible para el texto.

        Args:
            texto: Texto del usuario

        Returns:
            Respuesta rápida si aplica, None en caso contrario
        """
        for patron, respuesta in self.RESPUESTAS_RAPIDAS.items():
            if re.search(patron, texto.strip()):
                logger.info(f"Respuesta rápida aplicada para patrón: {patron}")
                return respuesta
        return None

    def obtener_o_crear_conversacion(self, usuario_id: str) -> Conversacion:
        """
        Obtiene una conversación existente o crea una nueva.
        OPTIMIZADO: Incluye cache para evitar consultas repetidas.
        """
        start_time = time.perf_counter()

        try:
            # Verificar cache primero
            if usuario_id in self._conversation_cache:
                cached_conv = self._conversation_cache[usuario_id]
                logger.debug(
                    f"Conversación obtenida del cache para {usuario_id}")
                return cached_conv

            # Intentar obtener una conversación existente
            conversacion = self.repository.obtener_conversacion_activa(
                usuario_id)

            # Si no existe, crear una nueva
            if not conversacion:
                # Obtener o crear usuario
                usuario = self.repository.obtener_usuario(usuario_id)
                if not usuario:
                    usuario = Usuario(id=usuario_id)
                    self.repository.guardar_usuario(usuario)

                # Crear nueva conversación
                conversacion_id = str(uuid.uuid4())
                conversacion = Conversacion(
                    id=conversacion_id, usuario=usuario)

                # Agregar mensaje del sistema
                conversacion.agregar_mensaje(self.mensaje_sistema)

                # Guardar la conversación
                self.repository.guardar_conversacion(conversacion)

            # Agregar al cache (limitar tamaño)
            self._add_to_conversation_cache(usuario_id, conversacion)

            execution_time = (time.perf_counter() - start_time) * 1000
            logger.debug(
                f"Conversación obtenida/creada en {execution_time:.2f}ms")

            return conversacion

        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"Error obteniendo conversación en {execution_time:.2f}ms: {e}")
            raise

    def _add_to_conversation_cache(self, usuario_id: str, conversacion: Conversacion):
        """Agrega conversación al cache con límite de tamaño"""
        if len(self._conversation_cache) >= self._max_cache_size:
            # Remover el más antiguo (FIFO simple)
            oldest_key = next(iter(self._conversation_cache))
            del self._conversation_cache[oldest_key]

        self._conversation_cache[usuario_id] = conversacion

    def agregar_mensaje_usuario(self, usuario_id: str, texto: str) -> Mensaje:
        """
        Agrega un mensaje del usuario a la conversación.
        """
        start_time = time.perf_counter()

        try:
            # Validación
            if not texto or not texto.strip():
                raise ValueError("El texto del mensaje no puede estar vacío")

            conversacion = self.obtener_o_crear_conversacion(usuario_id)

            # Crear mensaje con ID único
            mensaje = Mensaje(role="user", content=texto.strip())
            mensaje.id = str(uuid.uuid4())
            mensaje.timestamp = datetime.now()

            # Agregar a la conversación en memoria
            conversacion.agregar_mensaje(mensaje)

            # ✅ IMPORTANTE: Guardar mensaje individual PRIMERO
            # Esto asegura que el mensaje se guarde incluso si falla el guardado de la conversación
            if hasattr(self.repository, '_guardar_mensaje'):
                self.repository._guardar_mensaje(conversacion.id, mensaje)
                logger.info(f"✅ Mensaje individual guardado: {mensaje.id}")
            
            # Luego actualizar la conversación completa
            self.repository.guardar_conversacion(conversacion)

            # Actualizar cache
            self._conversation_cache[usuario_id] = conversacion

            execution_time = (time.perf_counter() - start_time) * 1000
            logger.info(f"✅ Mensaje usuario procesado en {execution_time:.2f}ms")

            return mensaje

        except Exception as e:
            logger.error(f"❌ Error agregando mensaje usuario: {e}")
            raise
        
    def agregar_mensaje_asistente(self, usuario_id: str, texto: str) -> Mensaje:
        """
        Agrega un mensaje del asistente a la conversación.
        ✅ MEJORADO: Asegura que cada mensaje tenga un ID único.
        """
        start_time = time.perf_counter()

        try:
            conversacion = self.obtener_o_crear_conversacion(usuario_id)

            # Crear mensaje con ID único
            mensaje = Mensaje(role="assistant", content=texto)
            mensaje.id = str(uuid.uuid4())  # ✅ Asignar ID inmediatamente
            mensaje.timestamp = datetime.now()

            # Agregar a la conversación
            conversacion.agregar_mensaje(mensaje)

            # ✅ Guardar mensaje individual primero (más seguro)
            if hasattr(self.repository, '_guardar_mensaje_individual'):
                self.repository._guardar_mensaje_individual(conversacion.id, mensaje)
            
            # Luego guardar la conversación completa
            self.repository.guardar_conversacion(conversacion)

            # Actualizar cache
            self._conversation_cache[usuario_id] = conversacion

            execution_time = (time.perf_counter() - start_time) * 1000
            logger.info(f"✅ Mensaje asistente agregado en {execution_time:.2f}ms - ID: {mensaje.id}")

            return mensaje

        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.error(f"❌ Error agregando mensaje asistente en {execution_time:.2f}ms: {e}")
            raise
    
    def _estimar_tokens(self, texto: str) -> int:
        """
        Estima el número de tokens en un texto.
        Aproximación simple: ~1 token por cada 4 caracteres.
        """
        return len(texto) // 4
    
    def _determinar_tono_respuesta(self, sentiment: str, is_escalation: bool) -> str:
        """
        Determina el tono apropiado para la respuesta basado en el contexto.
        """
        if is_escalation:
            return "empathetic_supportive"
        elif sentiment == "negativo":
            return "empathetic_helpful"
        elif sentiment == "positivo":
            return "friendly_professional"
        else:
            return "professional_neutral"
    
    def _detectar_intent(self, texto: str) -> str:
        """
        Detecta el intent del mensaje usando reglas simples.
        En producción, esto debería usar un servicio de NLU.
        """
        texto_lower = texto.lower()
        
        # Detección básica de intents bancarios
        if any(word in texto_lower for word in ['saldo', 'cuánto tengo', 'mi cuenta']):
            return 'consulta_saldo'
        elif any(word in texto_lower for word in ['transferir', 'transferencia', 'enviar dinero']):
            return 'transferencia'
        elif any(word in texto_lower for word in ['préstamo', 'crédito', 'prestar']):
            return 'prestamo'
        elif any(word in texto_lower for word in ['tarjeta', 'débito', 'crédito']):
            return 'tarjeta'
        elif any(word in texto_lower for word in ['ayuda', 'problema', 'no funciona', 'error']):
            return 'soporte'
        elif any(word in texto_lower for word in ['hola', 'buenos días', 'buenas tardes']):
            return 'saludo'
        else:
            return 'consulta_general'
        
    def _check_escalation_keywords(self, texto: str) -> bool:
        """
        Verifica si el mensaje contiene palabras clave de escalación.
        """
        escalation_keywords = [
            'hablar con humano', 'agente humano', 'persona real',
            'operador', 'no entiendes', 'no me ayudas',
            'quiero hablar con alguien', 'transferir a agente'
        ]
        
        texto_lower = texto.lower()
        return any(keyword in texto_lower for keyword in escalation_keywords)
    
    def procesar_mensaje(self, usuario_id: str, texto_mensaje: str) -> str:
        """
        Procesa un mensaje de un usuario, incluyendo análisis completo de sentimiento y métricas.
        ✅ ACTUALIZADO: Guarda TODOS los campos de análisis correctamente
        """
        # --- INICIO DE LA MEDICIÓN ---
        start_time = time.perf_counter()
        ai_start_time = None
        ai_end_time = None

        try:
            # 1. Obtener o crear conversación
            conversacion = self.obtener_o_crear_conversacion(usuario_id)
            
            # 2. Analizar sentimiento completo del mensaje del usuario
            # Si ai_provider tiene análisis de sentimiento, usarlo
            if hasattr(self.ai_provider, 'analizar_sentimiento'):
                analysis_result = self.ai_provider.analizar_sentimiento(texto_mensaje)
                sentiment = analysis_result.get("sentimiento", "neutral")
                sentiment_confidence = float(analysis_result.get("confianza", 0.5))
                emociones = analysis_result.get("emociones", [])
                intent = analysis_result.get("intent", self._detectar_intent(texto_mensaje))
                intent_confidence = float(analysis_result.get("intent_confidence", 0.7))
                is_escalation_request = analysis_result.get("escalacion_requerida", False)
                detected_entities = analysis_result.get("entidades", {})
                suggested_tone = analysis_result.get("tono_sugerido", "professional")
            else:
                # Fallback: usar sentimiento_analyzer tradicional
                analisis = self.sentimiento_analyzer.execute(texto_mensaje)
                sentiment = analisis.sentimiento if analisis else "neutral"
                sentiment_confidence = analisis.confianza if analisis else 0.5
                emociones = analisis.emociones if hasattr(analisis, 'emociones') else []
                intent = self._detectar_intent(texto_mensaje)
                intent_confidence = 0.8
                is_escalation_request = self._check_escalation_keywords(texto_mensaje)
                detected_entities = {}
                suggested_tone = "professional"
                analysis_result = {
                    "sentimiento": sentiment,
                    "confianza": sentiment_confidence,
                    "emociones": emociones,
                    "intent": intent,
                    "intent_confidence": intent_confidence,
                    "entidades": detected_entities,
                    "escalacion_requerida": is_escalation_request,
                    "tono_sugerido": suggested_tone
                }
            
            # 3. ✅ NUEVO: Crear mensaje del usuario con TODOS los campos de análisis
            mensaje_usuario = Mensaje(role="user", content=texto_mensaje)
            mensaje_usuario.id = str(uuid.uuid4())
            mensaje_usuario.timestamp = datetime.now()
            
            # Asignar TODOS los campos del análisis de sentimiento
            mensaje_usuario.sentiment = sentiment
            mensaje_usuario.sentiment_score = sentiment_confidence  # Para compatibilidad
            mensaje_usuario.sentiment_confidence = sentiment_confidence
            mensaje_usuario.intent = intent
            mensaje_usuario.intent_confidence = intent_confidence
            mensaje_usuario.is_escalation_request = is_escalation_request
            mensaje_usuario.metadata = {
                "analysis_result": analysis_result,
                "detected_entities": detected_entities,
                "suggested_tone": suggested_tone,
                "emociones": emociones
            }
            
            # 4. Agregar mensaje a la conversación
            conversacion.agregar_mensaje(mensaje_usuario)
            
            # 5. ✅ IMPORTANTE: Guardar mensaje del usuario inmediatamente
            if hasattr(self.repository, '_guardar_mensaje'):
                self.repository._guardar_mensaje(conversacion.id, mensaje_usuario)
                logger.debug(f"Mensaje usuario guardado con análisis completo")
            
            # 6. Generar respuesta de la IA
            historial_mensajes = conversacion.obtener_historial()
            
            # Medir tiempo específico de IA
            ai_start_time = time.perf_counter()
            respuesta_ia = self.ai_provider.generar_respuesta(historial_mensajes)
            ai_end_time = time.perf_counter()
            ai_processing_time_ms = (ai_end_time - ai_start_time) * 1000
            
            # 7. Contar tokens y determinar tono de respuesta
            token_count = self._estimar_tokens(texto_mensaje + respuesta_ia)
            response_tone = self._determinar_tono_respuesta(sentiment, is_escalation_request)

            # --- FIN DE LA MEDICIÓN ---
            end_time = time.perf_counter()
            processing_time_ms = (end_time - start_time) * 1000

            # 8. ✅ Crear y guardar mensaje del bot
            mensaje_bot = Mensaje(role="assistant", content=respuesta_ia)
            mensaje_bot.id = str(uuid.uuid4())
            mensaje_bot.timestamp = datetime.now()
            mensaje_bot.token_count = self._estimar_tokens(respuesta_ia)
            mensaje_bot.response_tone = response_tone
            mensaje_bot.ai_processing_time_ms = round(ai_processing_time_ms)
            mensaje_bot.metadata = {
                "response_tone": response_tone,
                "ai_processing_time_ms": round(ai_processing_time_ms)
            }
            
            # 9. Agregar mensaje del bot a la conversación
            conversacion.agregar_mensaje(mensaje_bot)
            
            # 10. ✅ Guardar mensaje del bot individualmente
            if hasattr(self.repository, '_guardar_mensaje'):
                self.repository._guardar_mensaje(conversacion.id, mensaje_bot)
                logger.debug(f"Mensaje bot guardado individualmente: {mensaje_bot.id}")
            
            # 11. ✅ Actualizar métricas finales del mensaje usuario
            mensaje_usuario.processing_time_ms = round(processing_time_ms)
            mensaje_usuario.ai_processing_time_ms = round(ai_processing_time_ms)
            mensaje_usuario.token_count = token_count
            mensaje_usuario.response_tone = response_tone
            
            mensaje_usuario.metadata.update({
                "processing_time_ms": round(processing_time_ms),
                "ai_processing_time_ms": round(ai_processing_time_ms)
            })
            
            # 12. ✅ Actualizar el mensaje del usuario en la BD con tiempos finales
            if hasattr(self.repository, '_guardar_mensaje'):
                self.repository._guardar_mensaje(conversacion.id, mensaje_usuario)
                logger.debug(f"Mensaje usuario actualizado con tiempos finales")
            
            # 13. Guardar la conversación completa
            self.repository.guardar_conversacion(conversacion)
            
            # 14. Actualizar cache
            self._conversation_cache[usuario_id] = conversacion
            
            logger.info(
                f"✅ Mensaje procesado para {usuario_id} en {processing_time_ms:.2f}ms "
                f"(IA: {ai_processing_time_ms:.2f}ms) | Sentimiento: {sentiment} ({sentiment_confidence:.2f}) | "
                f"Intent: {intent} ({intent_confidence:.2f}) | Tokens: {token_count}"
            )
            
            return respuesta_ia

        except Exception as e:
            logger.error(f"❌ Error procesando mensaje para {usuario_id}: {e}", exc_info=True)
            return "Lo siento, ocurrió un error inesperado al procesar tu mensaje."

    def _generar_cache_key(self, usuario_id: str, texto: str) -> str:
        """Genera clave de cache basada en el mensaje y contexto reciente"""
        import hashlib
        # Usar solo últimas palabras del mensaje para generalizar
        palabras = texto.lower().strip().split()
        texto_reducido = " ".join(
            palabras[-5:]) if len(palabras) > 5 else texto.lower().strip()
        return hashlib.md5(f"{usuario_id}_{texto_reducido}".encode()).hexdigest()

    def _add_to_response_cache(self, cache_key: str, respuesta: str):
        """Agrega respuesta al cache con límite de tamaño"""
        if len(self._response_cache) >= self._max_cache_size:
            oldest_key = next(iter(self._response_cache))
            del self._response_cache[oldest_key]

        self._response_cache[cache_key] = respuesta

    def obtener_historial_mensajes(self, usuario_id: str, limit: int = 15) -> List[Dict[str, str]]:
        """
        MÉTODO OPTIMIZADO: Obtiene historial limitado.
        """
        start_time = time.perf_counter()

        try:
            conversacion = self.obtener_o_crear_conversacion(usuario_id)
            historial_completo = conversacion.obtener_historial()

            # Aplicar límite manteniendo mensaje de sistema
            if len(historial_completo) > limit:
                sistema_msgs = [
                    m for m in historial_completo if m.get('role') == 'system']
                otros_msgs = [
                    m for m in historial_completo if m.get('role') != 'system']
                historial_limitado = sistema_msgs + \
                    otros_msgs[-(limit - len(sistema_msgs)):]
            else:
                historial_limitado = historial_completo

            execution_time = (time.perf_counter() - start_time) * 1000
            logger.debug(f"Historial obtenido en {execution_time:.2f}ms")

            return historial_limitado

        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"Error obteniendo historial en {execution_time:.2f}ms: {e}")
            return [{"role": "system", "content": "Eres un asistente bancario virtual."}]

    def obtener_resumen_conversacion(self, usuario_id: str) -> str:
        """
        Genera un resumen de la conversación para mantener contexto.
        """
        start_time = time.perf_counter()

        try:
            conversacion = self.obtener_o_crear_conversacion(usuario_id)

            # Si hay pocos mensajes, no es necesario resumir
            if len(conversacion.mensajes) < 15:
                return ""

            # Solicitar un resumen a la IA
            # Últimos 10 mensajes
            mensajes_para_resumir = conversacion.mensajes[-10:]
            mensajes_formateados = [
                f"{m.role}: {m.content}" for m in mensajes_para_resumir]

            instruccion = "Resume brevemente los siguientes intercambios de la conversación manteniendo los puntos clave:"
            contenido = "\n".join(mensajes_formateados)

            mensajes_resumen = [
                {"role": "system", "content": instruccion},
                {"role": "user", "content": contenido}
            ]

            if self.ai_provider:
                respuesta = self.ai_provider.generar_respuesta(
                    mensajes_resumen)
                execution_time = (time.perf_counter() - start_time) * 1000
                logger.debug(f"Resumen generado en {execution_time:.2f}ms")
                return respuesta
            else:
                logger.warning(
                    "AI provider no disponible para generar resumen")
                return ""

        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"Error generando resumen en {execution_time:.2f}ms: {e}")
            return ""

    def actualizar_datos_usuario(self, usuario_id: str, datos: Dict) -> None:
        """
        Actualiza los datos del usuario.
        """
        start_time = time.perf_counter()

        try:
            usuario = self.repository.obtener_usuario(usuario_id)
            if usuario:
                usuario.datos.update(datos)
                self.repository.guardar_usuario(usuario)

                execution_time = (time.perf_counter() - start_time) * 1000
                logger.debug(
                    f"Datos usuario actualizados en {execution_time:.2f}ms")
            else:
                logger.warning(
                    f"Usuario {usuario_id} no encontrado para actualizar datos")

        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"Error actualizando datos usuario en {execution_time:.2f}ms: {e}")

    def analizar_sentimiento_mensaje(self, texto: str) -> AnalisisSentimiento:
        """
        Analiza el sentimiento de un mensaje con cache.
        """
        start_time = time.perf_counter()

        try:
            # Crear clave de cache
            cache_key = hash(texto.strip().lower())

            # Verificar cache
            if cache_key in self._sentiment_cache:
                execution_time = (time.perf_counter() - start_time) * 1000
                logger.debug(
                    f"Sentimiento obtenido del cache en {execution_time:.2f}ms")
                return self._sentiment_cache[cache_key]

            # Analizar sentimiento
            resultado = self.sentimiento_analyzer.execute(texto)

            # Agregar al cache con límite
            if len(self._sentiment_cache) >= self._max_cache_size:
                oldest_key = next(iter(self._sentiment_cache))
                del self._sentiment_cache[oldest_key]

            self._sentiment_cache[cache_key] = resultado

            execution_time = (time.perf_counter() - start_time) * 1000
            logger.debug(f"Sentimiento analizado en {execution_time:.2f}ms")

            return resultado

        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"Error analizando sentimiento en {execution_time:.2f}ms: {e}")

            # Retornar análisis por defecto
            class FallbackSentiment:
                sentimiento = "neutral"
                confianza = 0.5
                emociones = []
                entidades = {}

            return FallbackSentiment()

    def check_for_escalation(self, mensaje_usuario: str, usuario_id: str) -> bool:
        """
        Verifica si es necesario escalar la conversación a un humano.
        """
        start_time = time.perf_counter()

        try:
            # Si no hay servicio de escalación, no se puede escalar
            if not self.escalation_service:
                logger.debug("Escalation service no disponible")
                return False

            # Obtener conversación activa
            conversacion = self.obtener_o_crear_conversacion(usuario_id)

            # Verificar si debe escalar
            should_escalate, reason = self.escalation_service.check_for_escalation(
                mensaje_usuario, conversacion)

            # Si debe escalar, crear ticket
            if should_escalate and reason:
                # Obtener usuario
                usuario = self.repository.obtener_usuario(usuario_id)

                # Crear ticket
                ticket = self.escalation_service.create_ticket(
                    conversacion, usuario, reason)

                execution_time = (time.perf_counter() - start_time) * 1000
                logger.info(
                    f"Conversación escalada en {execution_time:.2f}ms. Ticket creado: {ticket.id}")
                return True

            execution_time = (time.perf_counter() - start_time) * 1000
            logger.debug(
                f"Verificación escalación completada en {execution_time:.2f}ms")
            return False

        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"Error verificando escalación en {execution_time:.2f}ms: {e}")
            return False

    def esta_escalada(self, usuario_id: str) -> bool:
        """
        Verifica si la conversación ya ha sido escalada a un humano.
        """
        start_time = time.perf_counter()

        try:
            if not self.escalation_service:
                return False

            # Verificar si hay tickets activos para este usuario
            tickets_activos = self.escalation_service.get_active_tickets(
                usuario_id)

            execution_time = (time.perf_counter() - start_time) * 1000
            logger.debug(
                f"Verificación estado escalación en {execution_time:.2f}ms")

            return len(tickets_activos) > 0

        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"Error verificando estado escalación en {execution_time:.2f}ms: {e}")
            return False