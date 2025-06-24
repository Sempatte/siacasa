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
        ✅ CLAVE: Guarda conversación Y mensajes en PostgreSQL.
        
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
            
            # 2. ✅ CRÍTICO: Guardar TODOS los mensajes en PostgreSQL
            if hasattr(conversacion, 'mensajes') and conversacion.mensajes:
                with self.db.get_connection() as conn:
                    with conn.cursor() as cur:
                        # Borrar mensajes antiguos para luego insertar todos (estrategia simple)
                        cur.execute("DELETE FROM mensajes WHERE conversacion_id = %s", (conversacion.id,))
                        
                        # Insertar todos los mensajes de nuevo
                        for mensaje in conversacion.mensajes:
                            cur.execute(
                                """
                                INSERT INTO mensajes (id, conversacion_id, role, content, timestamp, sentimental_score, processing_time_ms)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                """,
                                (
                                    mensaje.id,
                                    conversacion.id,
                                    mensaje.role,
                                    mensaje.content,
                                    mensaje.timestamp,
                                    # Asegúrate de que estos valores se pasen
                                    getattr(mensaje, 'sentimental_score', None),
                                    getattr(mensaje, 'processing_time_ms', None)
                                )
                            )
                        conn.commit()
            
            logger.info(f"✅ Conversación guardada en PostgreSQL: {conversacion.id} "
                       f"con {len(conversacion.mensajes)} mensajes")
                       
        except Exception as e:
            logger.error(f"❌ Error guardando conversación {conversacion.id}: {e}", exc_info=True)
            raise
    
    def _guardar_mensaje(self, conversacion_id: str, mensaje: Mensaje) -> None:
        """
        ✅ CRÍTICO: Guarda mensaje individual en PostgreSQL.
        
        Args:
            conversacion_id: ID de la conversación
            mensaje: Mensaje a guardar
        """
        try:
            # Generar ID si no existe
            mensaje_id = getattr(mensaje, 'id', None) or str(uuid.uuid4())
            
            self.db.execute("""
                INSERT INTO mensajes (
                    id, conversacion_id, role, content, 
                    timestamp, metadata
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    content = EXCLUDED.content,
                    metadata = EXCLUDED.metadata
            """, (
                mensaje_id,
                conversacion_id,
                mensaje.role,
                mensaje.content,
                getattr(mensaje, 'timestamp', datetime.now()),
                json.dumps({})
            ))
            
            # Asignar ID al mensaje si no lo tenía
            if not hasattr(mensaje, 'id'):
                mensaje.id = mensaje_id
                
        except Exception as e:
            logger.error(f"Error guardando mensaje: {e}")
    
    def obtener_conversacion(self, conversacion_id: str) -> Optional[Conversacion]:
        """
        Obtiene una conversación de PostgreSQL.
        
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
            
            # ✅ Cargar mensajes de PostgreSQL
            mensajes_data = self.db.fetch_all("""
                SELECT id, role, content, timestamp, metadata
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
