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
        OPTIMIZADO: Medición de tiempo y validación de entrada.
        """
        start_time = time.perf_counter()

        try:
            # Validación de entrada
            if not texto or not texto.strip():
                raise ValueError("El texto del mensaje no puede estar vacío")

            conversacion = self.obtener_o_crear_conversacion(usuario_id)

            # Crear mensaje
            mensaje = Mensaje(role="user", content=texto.strip())

            # Agregar a la conversación
            conversacion.agregar_mensaje(mensaje)

            # OPTIMIZACIÓN: Limitar historial para evitar tokens excesivos
            conversacion.limitar_historial(max_mensajes=15)

            # Guardar la conversación actualizada
            self.repository.guardar_conversacion(conversacion)

            # Actualizar cache
            self._conversation_cache[usuario_id] = conversacion

            execution_time = (time.perf_counter() - start_time) * 1000
            logger.debug(f"Mensaje usuario agregado en {execution_time:.2f}ms")

            return mensaje

        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"Error agregando mensaje usuario en {execution_time:.2f}ms: {e}")
            raise

    def agregar_mensaje_asistente(self, usuario_id: str, texto: str) -> Mensaje:
        """
        Agrega un mensaje del asistente a la conversación.
        OPTIMIZADO: Medición de tiempo y cache actualizado.
        """
        start_time = time.perf_counter()

        try:
            conversacion = self.obtener_o_crear_conversacion(usuario_id)

            # Crear mensaje
            mensaje = Mensaje(role="assistant", content=texto)

            # Agregar a la conversación
            conversacion.agregar_mensaje(mensaje)

            # Guardar la conversación actualizada
            self.repository.guardar_conversacion(conversacion)

            # Actualizar cache
            self._conversation_cache[usuario_id] = conversacion

            execution_time = (time.perf_counter() - start_time) * 1000
            logger.debug(
                f"Mensaje asistente agregado en {execution_time:.2f}ms")

            return mensaje

        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"Error agregando mensaje asistente en {execution_time:.2f}ms: {e}")
            raise

    def procesar_mensaje(self, usuario_id: str, texto: str, info_usuario: Dict = None) -> str:
        """
        🔥 MÉTODO PRINCIPAL OPTIMIZADO: Procesa mensajes con respuestas rápidas y cache.
        """
        start_time = time.perf_counter()

        try:
            # 1. RESPUESTA INSTANTÁNEA si es posible
            respuesta_rapida = self.obtener_respuesta_rapida(texto)
            if respuesta_rapida:
                # Agregar mensaje del usuario y respuesta al historial
                self.agregar_mensaje_usuario(usuario_id, texto)
                self.agregar_mensaje_asistente(usuario_id, respuesta_rapida)

                execution_time = (time.perf_counter() - start_time) * 1000
                logger.info(f"✅ Respuesta rápida en {execution_time:.2f}ms")
                return respuesta_rapida

            # 2. Verificar cache de respuestas
            cache_key = self._generar_cache_key(usuario_id, texto)
            if cache_key in self._response_cache:
                cached_response = self._response_cache[cache_key]
                execution_time = (time.perf_counter() - start_time) * 1000
                logger.info(f"✅ Respuesta del cache en {execution_time:.2f}ms")
                return cached_response

            # 3. Obtener conversación existente
            conversacion = self.obtener_o_crear_conversacion(usuario_id)

            logger.info(
                f"🔍 CONVERSACIÓN {usuario_id}: {len(conversacion.mensajes)} mensajes existentes")

            # 4. Agregar mensaje del usuario
            self.agregar_mensaje_usuario(usuario_id, texto)

            # 5. Obtener historial optimizado (máximo 15 mensajes)
            historial_completo = conversacion.obtener_historial()

            # Limitar historial para optimizar velocidad
            if len(historial_completo) > 15:
                sistema_msgs = [
                    m for m in historial_completo if m.get('role') == 'system']
                otros_msgs = [
                    m for m in historial_completo if m.get('role') != 'system']
                historial_completo = sistema_msgs + \
                    otros_msgs[-14:]  # Sistema + últimos 14

            logger.info(
                f"✅ Enviando {len(historial_completo)} mensajes a la IA")

            # 6. Generar respuesta con IA
            if not self.ai_provider:
                logger.error("❌ AI provider no disponible")
                return "Lo siento, estoy experimentando problemas técnicos."

            respuesta = self.ai_provider.generar_respuesta(historial_completo)

            # 7. Guardar respuesta del asistente
            mensaje_respuesta = Mensaje(
                role="assistant",
                content=respuesta,
                timestamp=datetime.now()
            )
            conversacion.agregar_mensaje(mensaje_respuesta)

            # 8. Guardar conversación y actualizar cache
            self.repository.guardar_conversacion(conversacion)
            self._conversation_cache[usuario_id] = conversacion

            # 9. Agregar respuesta al cache
            self._add_to_response_cache(cache_key, respuesta)

            execution_time = (time.perf_counter() - start_time) * 1000
            logger.info(f"✅ Respuesta IA generada en {execution_time:.2f}ms")

            return respuesta

        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"❌ Error procesando mensaje en {execution_time:.2f}ms: {e}", exc_info=True)
            return "Disculpa, ocurrió un error al procesar tu mensaje. ¿Puedes intentarlo de nuevo?"

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
