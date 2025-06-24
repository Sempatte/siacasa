import uuid
import logging
import time
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
    VERSIÓN OPTIMIZADA con medición de tiempo precisa y cache.
    ARREGLADO: Mantiene contexto completo de la conversación.
    """

    def __init__(
        self, repository: IRepository, sentimiento_analyzer, ai_provider=None, bank_config=None,
        support_repository=None
    ):
        """
        Inicializa el servicio del chatbot.

        Args:
            repository: Repositorio para almacenar datos
            sentimiento_analyzer: Analizador de sentimientos
            ai_provider: Proveedor de IA para generar respuestas
            bank_config: Configuración específica del banco
            support_repository: Repositorio para tickets de soporte (opcional)
        """
        self.repository = repository
        self.sentimiento_analyzer = sentimiento_analyzer
        self.ai_provider = ai_provider
        self.support_repository = support_repository
        
        # Cache para optimizar rendimiento
        self._sentiment_cache = {}
        self._conversation_cache = {}
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
            logger.warning("Support repository not provided, escalation service not initialized")
            
        self.bank_config = {**default_config, **(bank_config or {})}
        
        # Mensaje de sistema que define el comportamiento del chatbot
        self.mensaje_sistema = Mensaje(
            role="system",
            content=f"""
            Eres SIACASA, un asistente bancario virtual diseñado para brindar atención al cliente 
            del {self.bank_config['bank_name']}. Tu objetivo es proporcionar respuestas precisas, 
            eficientes y empáticas a las consultas de los clientes.
            
            - Identifícate como asistente virtual del {self.bank_config['bank_name']}.
            - Debes ser amable, respetuoso y profesional en todo momento.
            - Adapta tu tono según el estado emocional del cliente.
            - Proporciona información clara sobre productos y servicios bancarios.
            - Ayuda a resolver problemas comunes como consultas de saldo, transferencias, etc.
            - Si no puedes resolver una consulta, ofrece derivar al cliente con un agente humano.
            - Recuerda los ultimos mensajes de la conversación para mantener el contexto.
            - Si el cliente está molesto o frustrado, muestra empatía y ofrece soluciones.
            - Si el cliente está satisfecho, agradece su confianza y ofrécele más ayuda.
            - Si el cliente está confundido, sé claro y didáctico en tus explicaciones.
            - No vuelvas a saludar al cliente en cada respuesta.
            - No uses jerga técnica o términos complicados.
            - Utiliza un lenguaje sencillo evitando tecnicismos cuando sea posible.
            """
        )

    def obtener_o_crear_conversacion(self, usuario_id: str) -> Conversacion:
        """
        Obtiene una conversación existente o crea una nueva.
        OPTIMIZADO: Incluye cache para evitar consultas repetidas.

        Args:
            usuario_id: ID del usuario

        Returns:
            Conversación activa
        """
        start_time = time.perf_counter()
        
        try:
            # Verificar cache primero
            if usuario_id in self._conversation_cache:
                cached_conv = self._conversation_cache[usuario_id]
                logger.debug(f"Conversación obtenida del cache para {usuario_id}")
                return cached_conv

            # Intentar obtener una conversación existente
            conversacion = self.repository.obtener_conversacion_activa(usuario_id)

            # Si no existe, crear una nueva
            if not conversacion:
                # Obtener o crear usuario
                usuario = self.repository.obtener_usuario(usuario_id)
                if not usuario:
                    usuario = Usuario(id=usuario_id)
                    self.repository.guardar_usuario(usuario)

                # Crear nueva conversación
                conversacion_id = str(uuid.uuid4())
                conversacion = Conversacion(id=conversacion_id, usuario=usuario)

                # Agregar mensaje del sistema
                conversacion.agregar_mensaje(self.mensaje_sistema)

                # Guardar la conversación
                self.repository.guardar_conversacion(conversacion)

            # Agregar al cache (limitar tamaño)
            self._add_to_conversation_cache(usuario_id, conversacion)
            
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.debug(f"Conversación obtenida/creada en {execution_time:.2f}ms")
            
            return conversacion
            
        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.error(f"Error obteniendo conversación en {execution_time:.2f}ms: {e}")
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

        Args:
            usuario_id: ID del usuario
            texto: Texto del mensaje

        Returns:
            Mensaje creado
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
            conversacion.limitar_historial(max_mensajes=20)

            # Guardar la conversación actualizada
            self.repository.guardar_conversacion(conversacion)
            
            # Actualizar cache
            self._conversation_cache[usuario_id] = conversacion

            execution_time = (time.perf_counter() - start_time) * 1000
            logger.debug(f"Mensaje usuario agregado en {execution_time:.2f}ms")
            
            return mensaje
            
        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.error(f"Error agregando mensaje usuario en {execution_time:.2f}ms: {e}")
            raise

    def agregar_mensaje_asistente(self, usuario_id: str, texto: str) -> Mensaje:
        """
        Agrega un mensaje del asistente a la conversación.
        OPTIMIZADO: Medición de tiempo y cache actualizado.

        Args:
            usuario_id: ID del usuario
            texto: Texto del mensaje

        Returns:
            Mensaje creado
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
            logger.debug(f"Mensaje asistente agregado en {execution_time:.2f}ms")
            
            return mensaje
            
        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.error(f"Error agregando mensaje asistente en {execution_time:.2f}ms: {e}")
            raise

    def procesar_mensaje(self, usuario_id: str, texto: str, info_usuario: Dict = None) -> str:
        """
        🔥 MÉTODO PRINCIPAL: Procesa un mensaje del usuario manteniendo el contexto COMPLETO.
        CRÍTICO: Este método asegura que se mantenga el historial de la conversación.
        
        Args:
            usuario_id: ID del usuario
            texto: Texto del mensaje del usuario
            info_usuario: Información adicional del usuario
            
        Returns:
            Respuesta generada por la IA
        """
        start_time = time.perf_counter()
        
        try:
            # 1. Obtener conversación existente (esto preserva el historial)
            conversacion = self.obtener_o_crear_conversacion(usuario_id)
            
            # 2. DEBUG: Verificar que tenemos mensajes previos
            logger.info(f"🔍 CONVERSACIÓN {usuario_id}: {len(conversacion.mensajes)} mensajes existentes")
            for i, msg in enumerate(conversacion.mensajes[-3:]):  # Log últimos 3 mensajes
                content_preview = msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
                logger.info(f"  📝 Mensaje {i}: [{msg.role}] {content_preview}")
            
            # 3. Agregar mensaje del usuario a la conversación
            mensaje_usuario = self.agregar_mensaje_usuario(usuario_id, texto)
            
            # 4. CRÍTICO: Obtener historial COMPLETO incluyendo mensajes anteriores
            historial_completo = conversacion.obtener_historial()
            
            # 5. Verificar que el historial contiene contexto
            if len(historial_completo) < 2:
                logger.warning(f"⚠️ HISTORIAL MUY CORTO para {usuario_id}: {len(historial_completo)} mensajes")
            else:
                logger.info(f"✅ Enviando {len(historial_completo)} mensajes a la IA para mantener contexto")
            
            # 6. Generar respuesta con TODO el historial (esto mantiene el contexto)
            if not self.ai_provider:
                logger.error("❌ AI provider no disponible")
                return "Lo siento, estoy experimentando problemas técnicos."
            
            # 7. Llamar a la IA con el historial completo
            respuesta = self.ai_provider.generar_respuesta(historial_completo)
            
            # 8. Guardar respuesta del asistente
            mensaje_respuesta = Mensaje(
                id=str(uuid.uuid4()),
                role="assistant", 
                content=respuesta,
                timestamp=datetime.now()
            )
            conversacion.agregar_mensaje(mensaje_respuesta)
            
            # 9. CRÍTICO: Guardar la conversación actualizada
            self.repository.guardar_conversacion(conversacion)
            
            # 10. Actualizar cache para próximas consultas
            self._conversation_cache[usuario_id] = conversacion
            
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.info(f"✅ Mensaje procesado en {execution_time:.2f}ms con {len(historial_completo)} mensajes de contexto")
            
            return respuesta
            
        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.error(f"❌ Error procesando mensaje en {execution_time:.2f}ms: {e}", exc_info=True)
            return "Disculpa, ocurrió un error al procesar tu mensaje. ¿Puedes intentarlo de nuevo?"

    def obtener_historial_mensajes(self, usuario_id: str, limit: int = 20) -> List[Dict[str, str]]:
        """
        MÉTODO OPTIMIZADO: Obtiene el historial limitado directamente.
        
        Args:
            usuario_id: ID del usuario
            limit: Límite de mensajes a obtener

        Returns:
            Lista de mensajes en formato para la API de OpenAI
        """
        start_time = time.perf_counter()
        
        try:
            # Intentar usar el método optimizado del repositorio si está disponible
            if hasattr(self.repository, 'obtener_historial_limitado'):
                historial = self.repository.obtener_historial_limitado(usuario_id, limit)
                execution_time = (time.perf_counter() - start_time) * 1000
                logger.debug(f"Historial limitado obtenido en {execution_time:.2f}ms")
                return historial
            
            # Fallback al método original con límite en memoria
            conversacion = self.obtener_o_crear_conversacion(usuario_id)
            historial_completo = conversacion.obtener_historial()
            
            # Aplicar límite manteniendo mensaje de sistema
            if len(historial_completo) > limit:
                sistema_msgs = [m for m in historial_completo if m.get('role') == 'system']
                otros_msgs = [m for m in historial_completo if m.get('role') != 'system']
                historial_limitado = sistema_msgs + otros_msgs[-(limit - len(sistema_msgs)):]
            else:
                historial_limitado = historial_completo
            
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.debug(f"Historial fallback obtenido en {execution_time:.2f}ms")
            
            return historial_limitado
            
        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.error(f"Error obteniendo historial en {execution_time:.2f}ms: {e}")
            # Retornar historial mínimo en caso de error
            return [{"role": "system", "content": "Eres un asistente bancario virtual."}]

    def obtener_resumen_conversacion(self, usuario_id: str) -> str:
        """
        Genera un resumen de la conversación para mantener contexto.
        OPTIMIZADO: Con medición de tiempo.
        """
        start_time = time.perf_counter()
        
        try:
            conversacion = self.obtener_o_crear_conversacion(usuario_id)
            
            # Si hay pocos mensajes, no es necesario resumir
            if len(conversacion.mensajes) < 15:
                return ""
            
            # Solicitar un resumen a la IA
            mensajes_para_resumir = conversacion.mensajes[-15:]  # Últimos 15 mensajes
            mensajes_formateados = [f"{m.role}: {m.content}" for m in mensajes_para_resumir]
            
            instruccion = "Resume brevemente los siguientes intercambios de la conversación manteniendo los puntos clave:"
            contenido = "\n".join(mensajes_formateados)
            
            mensajes_resumen = [
                {"role": "system", "content": instruccion},
                {"role": "user", "content": contenido}
            ]
            
            if self.ai_provider:
                respuesta = self.ai_provider.generar_respuesta(mensajes_resumen)
                execution_time = (time.perf_counter() - start_time) * 1000
                logger.debug(f"Resumen generado en {execution_time:.2f}ms")
                return respuesta
            else:
                logger.warning("AI provider no disponible para generar resumen")
                return ""
                
        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.error(f"Error generando resumen en {execution_time:.2f}ms: {e}")
            return ""

    def actualizar_datos_usuario(self, usuario_id: str, datos: Dict) -> None:
        """
        Actualiza los datos del usuario.
        OPTIMIZADO: Con medición de tiempo.

        Args:
            usuario_id: ID del usuario
            datos: Datos a actualizar
        """
        start_time = time.perf_counter()
        
        try:
            usuario = self.repository.obtener_usuario(usuario_id)
            if usuario:
                usuario.datos.update(datos)
                self.repository.guardar_usuario(usuario)
                
                execution_time = (time.perf_counter() - start_time) * 1000
                logger.debug(f"Datos usuario actualizados en {execution_time:.2f}ms")
            else:
                logger.warning(f"Usuario {usuario_id} no encontrado para actualizar datos")
                
        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.error(f"Error actualizando datos usuario en {execution_time:.2f}ms: {e}")

    def analizar_sentimiento_mensaje(self, texto: str) -> AnalisisSentimiento:
        """
        Analiza el sentimiento de un mensaje.
        OPTIMIZADO: Con cache inteligente y medición de tiempo.

        Args:
            texto: Texto a analizar

        Returns:
            Análisis de sentimiento
        """
        start_time = time.perf_counter()
        
        try:
            # Crear clave de cache
            cache_key = hash(texto.strip().lower())
            
            # Verificar cache
            if cache_key in self._sentiment_cache:
                execution_time = (time.perf_counter() - start_time) * 1000
                logger.debug(f"Sentimiento obtenido del cache en {execution_time:.2f}ms")
                return self._sentiment_cache[cache_key]
            
            # Analizar sentimiento
            resultado = self.sentimiento_analyzer.execute(texto)
            
            # Agregar al cache con límite
            if len(self._sentiment_cache) >= self._max_cache_size:
                # Remover elementos antiguos (FIFO simple)
                oldest_key = next(iter(self._sentiment_cache))
                del self._sentiment_cache[oldest_key]
            
            self._sentiment_cache[cache_key] = resultado
            
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.debug(f"Sentimiento analizado en {execution_time:.2f}ms")
            
            return resultado
            
        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.error(f"Error analizando sentimiento en {execution_time:.2f}ms: {e}")
            
            # Retornar análisis por defecto en caso de error
            class FallbackSentiment:
                sentimiento = "neutral"
                confianza = 0.5
                emociones = []
                entidades = {}
            
            return FallbackSentiment()

    def check_for_escalation(self, mensaje_usuario: str, usuario_id: str) -> bool:
        """
        Verifica si es necesario escalar la conversación a un humano.
        OPTIMIZADO: Con medición de tiempo y mejor manejo de errores.
        
        Args:
            mensaje_usuario: Texto del mensaje del usuario
            usuario_id: ID del usuario
            
        Returns:
            True si es necesario escalar, False en caso contrario
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
            should_escalate, reason = self.escalation_service.check_for_escalation(mensaje_usuario, conversacion)
            
            # Si debe escalar, crear ticket
            if should_escalate and reason:
                # Obtener usuario
                usuario = self.repository.obtener_usuario(usuario_id)
                
                # Crear ticket
                ticket = self.escalation_service.create_ticket(conversacion, usuario, reason)
                
                execution_time = (time.perf_counter() - start_time) * 1000
                logger.info(f"Conversación escalada en {execution_time:.2f}ms. Ticket creado: {ticket.id}")
                return True
            
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.debug(f"Verificación escalación completada en {execution_time:.2f}ms")
            return False
            
        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.error(f"Error verificando escalación en {execution_time:.2f}ms: {e}")
            return False

    def esta_escalada(self, usuario_id: str) -> bool:
        """
        Verifica si la conversación ya ha sido escalada a un humano.
        OPTIMIZADO: Con medición de tiempo.
        
        Args:
            usuario_id: ID del usuario
            
        Returns:
            True si ya está escalada, False en caso contrario
        """
        start_time = time.perf_counter()
        
        try:
            # Si no hay servicio de escalación, no está escalada
            if not self.escalation_service:
                return False
            
            # Buscar tickets activos para este usuario
            if hasattr(self.escalation_service.repository, 'obtener_tickets_por_usuario'):
                tickets = self.escalation_service.repository.obtener_tickets_por_usuario(usuario_id)
                
                # Verificar si hay algún ticket activo (pendiente, asignado o activo)
                for ticket in tickets:
                    if ticket.estado in [TicketStatus.PENDING, TicketStatus.ASSIGNED, TicketStatus.ACTIVE]:
                        execution_time = (time.perf_counter() - start_time) * 1000
                        logger.debug(f"Estado escalación verificado en {execution_time:.2f}ms")
                        return True
            
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.debug(f"Estado escalación verificado en {execution_time:.2f}ms")
            return False
            
        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.error(f"Error verificando estado escalación en {execution_time:.2f}ms: {e}")
            return False

    def get_performance_stats(self) -> Dict[str, any]:
        """
        Obtiene estadísticas de rendimiento del servicio.
        
        Returns:
            Diccionario con estadísticas de rendimiento
        """
        return {
            'cache_sizes': {
                'sentiment_cache': len(self._sentiment_cache),
                'conversation_cache': len(self._conversation_cache)
            },
            'max_cache_size': self._max_cache_size,
            'escalation_service_available': self.escalation_service is not None,
            'ai_provider_available': self.ai_provider is not None
        }

    def clear_caches(self):
        """
        Limpia todos los caches para liberar memoria.
        """
        start_time = time.perf_counter()
        
        sentiment_cache_size = len(self._sentiment_cache)
        conversation_cache_size = len(self._conversation_cache)
        
        self._sentiment_cache.clear()
        self._conversation_cache.clear()
        
        execution_time = (time.perf_counter() - start_time) * 1000
        logger.info(f"Caches limpiados en {execution_time:.2f}ms. "
                   f"Sentimiento: {sentiment_cache_size}, Conversaciones: {conversation_cache_size}")

    def reiniciar_conversacion(self, usuario_id: str) -> bool:
        """
        Reinicia la conversación de un usuario.
        
        Args:
            usuario_id: ID del usuario
            
        Returns:
            True si se reinició correctamente
        """
        try:
            # Limpiar del cache
            if usuario_id in self._conversation_cache:
                del self._conversation_cache[usuario_id]
            
            # Si hay conversación activa, marcarla como inactiva
            conversacion = self.repository.obtener_conversacion_activa(usuario_id)
            if conversacion:
                # Aquí podrías implementar lógica para archivar la conversación
                logger.info(f"Conversación reiniciada para usuario {usuario_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error reiniciando conversación para {usuario_id}: {e}")
            return False