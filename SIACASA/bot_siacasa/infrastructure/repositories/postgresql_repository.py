import logging
import uuid
import json
from datetime import datetime
from typing import Dict, Optional, List

from bot_siacasa.application.interfaces.repository_interface import IRepository
from bot_siacasa.domain.entities.usuario import Usuario
from bot_siacasa.domain.entities.conversacion import Conversacion
from bot_siacasa.domain.entities.mensaje import Mensaje
from bot_siacasa.infrastructure.db.neondb_connector import NeonDBConnector

logger = logging.getLogger(__name__)

class PostgreSQLRepository(IRepository):
    """
    ✅ IMPLEMENTACIÓN REAL para PostgreSQL/NeonDB.
    Esta es la clase que necesitas para que las métricas funcionen.
    """
    
    def __init__(self, db_connector: NeonDBConnector = None):
        """
        Inicializa el repositorio con PostgreSQL.
        
        Args:
            db_connector: Conector a NeonDB PostgreSQL
        """
        self.db = db_connector or NeonDBConnector()
        logger.info("PostgreSQL Repository inicializado con NeonDB")
    
    def guardar_usuario(self, usuario: Usuario) -> None:
        """
        Guarda un usuario en PostgreSQL.
        
        Args:
            usuario: Usuario a guardar
        """
        try:
            # Verificar si el usuario ya existe
            existing = self.db.fetch_one("""
                SELECT id FROM usuarios WHERE id = %s
            """, (usuario.id,))
            
            if existing:
                # Actualizar usuario existente
                self.db.execute("""
                    UPDATE usuarios SET 
                        datos = %s,
                        fecha_actualizacion = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (json.dumps(usuario.datos), usuario.id))
                logger.debug(f"Usuario actualizado: {usuario.id}")
            else:
                # Crear nuevo usuario
                self.db.execute("""
                    INSERT INTO usuarios (id, datos, fecha_creacion)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (id) DO UPDATE SET
                        datos = EXCLUDED.datos,
                        fecha_actualizacion = CURRENT_TIMESTAMP
                """, (usuario.id, json.dumps(usuario.datos)))
                logger.info(f"✅ Usuario guardado en PostgreSQL: {usuario.id}")
                
        except Exception as e:
            logger.error(f"❌ Error guardando usuario {usuario.id}: {e}", exc_info=True)
            raise
    
    def obtener_usuario(self, usuario_id: str) -> Optional[Usuario]:
        """
        Obtiene un usuario de PostgreSQL.
        
        Args:
            usuario_id: ID del usuario
            
        Returns:
            Usuario o None si no existe
        """
        try:
            result = self.db.fetch_one("""
                SELECT id, datos FROM usuarios WHERE id = %s
            """, (usuario_id,))
            
            if result:
                datos = json.loads(result['datos']) if result['datos'] else {}
                usuario = Usuario(id=result['id'], datos=datos)
                logger.debug(f"Usuario encontrado en PostgreSQL: {usuario_id}")
                return usuario
            else:
                logger.debug(f"Usuario no encontrado en PostgreSQL: {usuario_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error obteniendo usuario {usuario_id}: {e}")
            return None
    
    def guardar_conversacion(self, conversacion: Conversacion):
        """
        ✅ MEJORADO: Guarda conversación sin borrar mensajes existentes.
        Solo actualiza la metadata de la conversación.
        
        Args:
            conversacion: Conversación a guardar
        """
        try:
            # 1. Guardar/actualizar la conversación
            self.db.execute("""
                INSERT INTO conversaciones (
                    id, usuario_id, fecha_inicio, fecha_fin, 
                    cantidad_mensajes, metadata
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    fecha_fin = EXCLUDED.fecha_fin,
                    cantidad_mensajes = EXCLUDED.cantidad_mensajes,
                    metadata = EXCLUDED.metadata
            """, (
                conversacion.id,
                conversacion.usuario.id,
                conversacion.fecha_inicio,
                conversacion.fecha_fin,
                len(conversacion.mensajes),
                json.dumps({"activa": conversacion.fecha_fin is None})
            ))
            
            # 2. ✅ NO borramos mensajes existentes
            # Solo guardamos mensajes que no tengan ID (nuevos)
            if hasattr(conversacion, 'mensajes') and conversacion.mensajes:
                for mensaje in conversacion.mensajes:
                    # Solo guardar mensajes sin ID (nuevos)
                    if not hasattr(mensaje, 'id') or not mensaje.id:
                        mensaje.id = str(uuid.uuid4())
                        self._guardar_mensaje(conversacion.id, mensaje)
            
            logger.info(f"✅ Conversación actualizada en PostgreSQL: {conversacion.id}")
                       
        except Exception as e:
            logger.error(f"❌ Error guardando conversación {conversacion.id}: {e}", exc_info=True)
            raise
    
    def _guardar_mensaje_individual(self, conversacion_id: str, mensaje: Mensaje) -> None:
        """
        ✅ DEPRECATED: Usar _guardar_mensaje en su lugar.
        Mantenido por compatibilidad.
        """
        self._guardar_mensaje(conversacion_id, mensaje)
    
    def _guardar_mensaje(self, conversacion_id: str, mensaje: Mensaje) -> None:
        """
        ✅ Guarda un mensaje individual en PostgreSQL con TODOS los campos de análisis.
        
        Args:
            conversacion_id: ID de la conversación
            mensaje: Mensaje a guardar con todos sus campos de análisis
        """
        try:
            # Asegurar que el mensaje tenga ID
            if not hasattr(mensaje, 'id') or not mensaje.id:
                mensaje.id = str(uuid.uuid4())
            
            # Extraer metadata si existe
            metadata = getattr(mensaje, 'metadata', {})
            
            # UPSERT con TODOS los campos de análisis
            self.db.execute("""
                INSERT INTO mensajes (
                    id, 
                    conversacion_id, 
                    role, 
                    content, 
                    timestamp, 
                    sentiment_score, 
                    processing_time_ms,
                    ai_processing_time_ms,
                    sentiment,
                    sentiment_confidence,
                    intent,
                    intent_confidence,
                    token_count,
                    response_tone,
                    metadata
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    content = EXCLUDED.content,
                    timestamp = EXCLUDED.timestamp,
                    sentiment_score = EXCLUDED.sentiment_score,
                    processing_time_ms = EXCLUDED.processing_time_ms,
                    ai_processing_time_ms = EXCLUDED.ai_processing_time_ms,
                    sentiment = EXCLUDED.sentiment,
                    sentiment_confidence = EXCLUDED.sentiment_confidence,
                    intent = EXCLUDED.intent,
                    intent_confidence = EXCLUDED.intent_confidence,
                    token_count = EXCLUDED.token_count,
                    response_tone = EXCLUDED.response_tone,
                    metadata = EXCLUDED.metadata
            """, (
                mensaje.id,
                conversacion_id,
                mensaje.role,
                mensaje.content,
                getattr(mensaje, 'timestamp', datetime.now()),
                getattr(mensaje, 'sentiment_score', None),
                getattr(mensaje, 'processing_time_ms', None),
                getattr(mensaje, 'ai_processing_time_ms', metadata.get('ai_processing_time_ms')),
                getattr(mensaje, 'sentiment', None),
                getattr(mensaje, 'sentiment_confidence', None),
                getattr(mensaje, 'intent', None),
                getattr(mensaje, 'intent_confidence', None),
                getattr(mensaje, 'token_count', None),
                getattr(mensaje, 'response_tone', metadata.get('response_tone')),
                json.dumps(metadata) if metadata else None
            ))
            
            # Actualizar contador de mensajes si es un nuevo mensaje
            self.db.execute("""
                UPDATE conversaciones 
                SET cantidad_mensajes = (
                    SELECT COUNT(*) FROM mensajes WHERE conversacion_id = %s
                )
                WHERE id = %s
            """, (conversacion_id, conversacion_id))
            
            logger.debug(f"✅ Mensaje guardado con análisis completo: {mensaje.id}")
            
            # Log de valores para debugging (con manejo de None)
            sentiment = getattr(mensaje, 'sentiment', 'N/A')
            sentiment_conf = getattr(mensaje, 'sentiment_confidence', 0) or 0
            intent = getattr(mensaje, 'intent', 'N/A')
            intent_conf = getattr(mensaje, 'intent_confidence', 0) or 0
            tokens = getattr(mensaje, 'token_count', 0) or 0
            proc_time = getattr(mensaje, 'processing_time_ms', 0) or 0
            
            logger.debug(f"   - Sentiment: {sentiment} ({sentiment_conf:.2f})")
            logger.debug(f"   - Intent: {intent} ({intent_conf:.2f})")
            logger.debug(f"   - Tokens: {tokens}")
            logger.debug(f"   - Processing time: {proc_time:.2f}ms")
            
        except Exception as e:
            logger.error(f"❌ Error guardando mensaje individual: {e}", exc_info=True)
            raise
    
    def obtener_conversacion(self, conversacion_id: str) -> Optional[Conversacion]:
        """
        Obtiene una conversación de PostgreSQL con TODOS los campos de los mensajes.
        
        Args:
            conversacion_id: ID de la conversación
            
        Returns:
            Conversación o None si no existe
        """
        try:
            # Obtener conversación
            conv_data = self.db.fetch_one("""
                SELECT 
                    id, usuario_id, fecha_inicio, fecha_fin, 
                    cantidad_mensajes, metadata
                FROM conversaciones 
                WHERE id = %s
            """, (conversacion_id,))
            
            if not conv_data:
                return None
            
            # Obtener usuario
            usuario = self.obtener_usuario(conv_data['usuario_id'])
            if not usuario:
                # Crear usuario básico si no existe
                usuario = Usuario(id=conv_data['usuario_id'])
            
            # Crear conversación
            conversacion = Conversacion(
                id=conv_data['id'],
                usuario=usuario,
                fecha_inicio=conv_data['fecha_inicio'],
                fecha_fin=conv_data['fecha_fin']
            )
            
            # ✅ Cargar mensajes con TODOS los campos
            mensajes_data = self.db.fetch_all("""
                SELECT 
                    id, role, content, timestamp, metadata,
                    sentiment, sentiment_score, sentiment_confidence,
                    intent, intent_confidence, token_count,
                    processing_time_ms, ai_processing_time_ms,
                    response_tone
                FROM mensajes 
                WHERE conversacion_id = %s 
                ORDER BY timestamp ASC
            """, (conversacion_id,))
            
            for msg_data in mensajes_data:
                mensaje = Mensaje(
                    role=msg_data['role'],
                    content=msg_data['content'],
                    timestamp=msg_data['timestamp']
                )
                mensaje.id = msg_data['id']
                
                # Cargar todos los campos adicionales
                mensaje.sentiment = msg_data.get('sentiment')
                mensaje.sentiment_score = msg_data.get('sentiment_score')
                mensaje.sentiment_confidence = msg_data.get('sentiment_confidence')
                mensaje.intent = msg_data.get('intent')
                mensaje.intent_confidence = msg_data.get('intent_confidence')
                mensaje.token_count = msg_data.get('token_count')
                mensaje.processing_time_ms = msg_data.get('processing_time_ms')
                mensaje.ai_processing_time_ms = msg_data.get('ai_processing_time_ms')
                mensaje.response_tone = msg_data.get('response_tone')
                
                # Cargar metadata
                if msg_data.get('metadata'):
                    try:
                        mensaje.metadata = json.loads(msg_data['metadata'])
                    except:
                        mensaje.metadata = {}
                
                conversacion.mensajes.append(mensaje)
            
            logger.debug(f"Conversación cargada: {conversacion_id} con {len(conversacion.mensajes)} mensajes")
            return conversacion
            
        except Exception as e:
            logger.error(f"Error obteniendo conversación {conversacion_id}: {e}")
            return None
    
    def obtener_conversacion_activa(self, usuario_id: str) -> Optional[Conversacion]:
        """
        ✅ CRÍTICO: Obtiene conversación activa de PostgreSQL.
        
        Args:
            usuario_id: ID del usuario
            
        Returns:
            Conversación activa o None si no existe
        """
        try:
            # Buscar conversación activa (sin fecha_fin)
            conv_data = self.db.fetch_one("""
                SELECT id
                FROM conversaciones 
                WHERE usuario_id = %s 
                    AND fecha_fin IS NULL 
                ORDER BY fecha_inicio DESC 
                LIMIT 1
            """, (usuario_id,))
            
            if conv_data:
                return self.obtener_conversacion(conv_data['id'])
            else:
                logger.debug(f"No hay conversación activa para usuario: {usuario_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error obteniendo conversación activa para {usuario_id}: {e}")
            return None
    
    def obtener_conversaciones_usuario(self, usuario_id: str) -> List[Conversacion]:
        """
        Obtiene todas las conversaciones de un usuario.
        
        Args:
            usuario_id: ID del usuario
            
        Returns:
            Lista de conversaciones
        """
        try:
            conv_ids = self.db.fetch_all("""
                SELECT id
                FROM conversaciones 
                WHERE usuario_id = %s 
                ORDER BY fecha_inicio DESC
            """, (usuario_id,))
            
            conversaciones = []
            for conv_data in conv_ids:
                conv = self.obtener_conversacion(conv_data['id'])
                if conv:
                    conversaciones.append(conv)
            
            logger.debug(f"Obtenidas {len(conversaciones)} conversaciones para {usuario_id}")
            return conversaciones
            
        except Exception as e:
            logger.error(f"Error obteniendo conversaciones para {usuario_id}: {e}")
            return []
    
    def obtener_historial_limitado(self, usuario_id: str, limit: int = 20) -> List[Dict[str, str]]:
        """
        ✅ NUEVO: Método optimizado para MetricsCollector.
        
        Args:
            usuario_id: ID del usuario
            limit: Límite de mensajes
            
        Returns:
            Lista de mensajes en formato para IA
        """
        try:
            mensajes_data = self.db.fetch_all("""
                SELECT m.role, m.content, m.timestamp
                FROM mensajes m
                JOIN conversaciones c ON m.conversacion_id = c.id
                WHERE c.usuario_id = %s
                ORDER BY m.timestamp DESC
                LIMIT %s
            """, (usuario_id, limit))
            
            # Revertir orden para cronología correcta
            historial = []
            for msg in reversed(mensajes_data):
                historial.append({
                    'role': msg['role'],
                    'content': msg['content']
                })
            
            logger.debug(f"Historial limitado obtenido: {len(historial)} mensajes para {usuario_id}")
            return historial
            
        except Exception as e:
            logger.error(f"Error obteniendo historial limitado: {e}")
            return [{"role": "system", "content": "Eres un asistente bancario virtual."}]