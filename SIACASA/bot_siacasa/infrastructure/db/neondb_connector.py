# bot_siacasa/infrastructure/db/neondb_connector.py
import logging
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class NeonDBConnector:
    """
    Conector para la base de datos PostgreSQL en NeonDB.
    """
    
    def __init__(self, host=None, database=None, user=None, password=None):
        """
        Inicializa el conector con las credenciales de conexión.
        Utiliza variables de entorno si no se proporcionan parámetros.
        
        Args:
            host: Host de la base de datos
            database: Nombre de la base de datos
            user: Usuario
            password: Contraseña
        """
        self.host = host or os.getenv("NEONDB_HOST")
        self.database = database or os.getenv("NEONDB_DATABASE")
        self.user = user or os.getenv("NEONDB_USER")
        self.password = password or os.getenv("NEONDB_PASSWORD")
        
        # Verificar que se proporcionaron todas las credenciales
        if not all([self.host, self.database, self.user, self.password]):
            logger.error("Faltan credenciales para conectar a NeonDB")
            raise ValueError("Faltan credenciales para conectar a NeonDB")
        
        # Inicializar la base de datos si es necesario
        self._initialize_database()
    
    def _get_connection(self):
        """
        Establece una conexión a la base de datos.
        
        Returns:
            Conexión a la base de datos
        """
        try:
            connection = psycopg2.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password
            )
            return connection
        except Exception as e:
            logger.error(f"Error al conectar a NeonDB: {e}", exc_info=True)
            raise
    
    def _initialize_database(self):
        """
        Inicializa la base de datos creando las tablas necesarias si no existen.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Crear tablas necesarias
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS banks (
                code VARCHAR(10) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_users (
                id UUID PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL DEFAULT 'user',
                bank_code VARCHAR(10) REFERENCES banks(code),
                is_active BOOLEAN DEFAULT TRUE,
                last_login TIMESTAMP,
                reset_token TEXT,
                reset_token_expiry TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS training_files (
                id UUID PRIMARY KEY,
                filename VARCHAR(255) NOT NULL,
                original_filename VARCHAR(255) NOT NULL,
                file_path VARCHAR(255) NOT NULL,
                file_type VARCHAR(50),
                file_size INTEGER,
                bank_code VARCHAR(10) REFERENCES banks(code),
                uploaded_by UUID REFERENCES admin_users(id),
                status VARCHAR(20) DEFAULT 'pending',
                description TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP
            )
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS training_sessions (
                id UUID PRIMARY KEY,
                bank_code VARCHAR(10) REFERENCES banks(code),
                initiated_by UUID REFERENCES admin_users(id),
                status VARCHAR(20) DEFAULT 'pending',
                files_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP,
                log_file VARCHAR(255),
                results TEXT
            )
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS training_session_files (
                session_id UUID REFERENCES training_sessions(id),
                file_id UUID REFERENCES training_files(id),
                status VARCHAR(20) DEFAULT 'pending',
                error_message TEXT,
                processed_at TIMESTAMP,
                PRIMARY KEY (session_id, file_id)
            )
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS chatbot_sessions (
                id UUID PRIMARY KEY,
                user_id VARCHAR(100) NOT NULL,
                bank_code VARCHAR(10) REFERENCES banks(code),
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP,
                message_count INTEGER DEFAULT 0,
                user_satisfied BOOLEAN,
                metadata JSONB
            )
            """)
            
            # Insertar banco por defecto si no existe
            cursor.execute("""
            INSERT INTO banks (code, name, description)
            VALUES ('default', 'Banco Predeterminado', 'Configuración predeterminada del sistema')
            ON CONFLICT (code) DO NOTHING
            """)
            
            # Insertar usuario administrador por defecto si no existe
            cursor.execute("""
            SELECT COUNT(*) FROM admin_users WHERE username = 'admin'
            """)
            admin_exists = cursor.fetchone()[0] > 0
            
            if not admin_exists:
                # La contraseña predeterminada es "admin123" (hash generado con werkzeug.security)
                cursor.execute("""
                INSERT INTO admin_users (
                    id, name, email, username, password_hash, role, bank_code
                )
                VALUES (
                    '00000000-0000-0000-0000-000000000000',
                    'Administrador',
                    'admin@siacasa.com',
                    'admin',
                    'pbkdf2:sha256:600000$LmQ0xnZDHkFGPxBn$5c9507f254be938ed982fb40ec78b19e68c3a3be7d88e9e91e5ed67a2384a571',
                    'admin',
                    'default'
                )
                """)
            
            conn.commit()
            logger.info("Base de datos inicializada correctamente")
            
        except Exception as e:
            logger.error(f"Error al inicializar la base de datos: {e}", exc_info=True)
            raise
        finally:
            if 'conn' in locals() and conn:
                conn.close()
    
    def execute(self, query: str, params: tuple = None) -> int:
        """
        Ejecuta una consulta SQL que no devuelve resultados.
        
        Args:
            query: Consulta SQL
            params: Parámetros para la consulta
            
        Returns:
            Número de filas afectadas
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            affected_rows = cursor.rowcount
            conn.commit()
            return affected_rows
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error al ejecutar consulta: {e}", exc_info=True)
            raise
        finally:
            if conn:
                conn.close()
    
    def fetch_one(self, query: str, params: tuple = None) -> Optional[Dict[str, Any]]:
        """
        Ejecuta una consulta SQL y devuelve una fila como diccionario.
        
        Args:
            query: Consulta SQL
            params: Parámetros para la consulta
            
        Returns:
            Diccionario con los resultados o None si no hay resultados
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query, params or ())
            result = cursor.fetchone()
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error al ejecutar consulta fetch_one: {e}", exc_info=True)
            raise
        finally:
            if conn:
                conn.close()
    
    def fetch_all(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """
        Ejecuta una consulta SQL y devuelve todas las filas como lista de diccionarios.
        
        Args:
            query: Consulta SQL
            params: Parámetros para la consulta
            
        Returns:
            Lista de diccionarios con los resultados
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query, params or ())
            results = cursor.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error al ejecutar consulta fetch_all: {e}", exc_info=True)
            raise
        finally:
            if conn:
                conn.close()
    
    # Métodos específicos para el panel de administración
    
    def get_conversation_count(self, bank_code: str) -> int:
        """
        Obtiene el número total de conversaciones para un banco.
        
        Args:
            bank_code: Código del banco
            
        Returns:
            Número de conversaciones
        """
        query = "SELECT COUNT(*) as count FROM chatbot_sessions WHERE bank_code = %s"
        result = self.fetch_one(query, (bank_code,))
        return result['count'] if result else 0
    
    def get_training_file_count(self, bank_code: str) -> int:
        """
        Obtiene el número total de archivos de entrenamiento para un banco.
        
        Args:
            bank_code: Código del banco
            
        Returns:
            Número de archivos
        """
        query = "SELECT COUNT(*) as count FROM training_files WHERE bank_code = %s"
        result = self.fetch_one(query, (bank_code,))
        return result['count'] if result else 0
    
    def get_last_training_date(self, bank_code: str) -> Optional[datetime]:
        """
        Obtiene la fecha del último entrenamiento para un banco.
        
        Args:
            bank_code: Código del banco
            
        Returns:
            Fecha del último entrenamiento o None si no hay entrenamientos
        """
        query = """
        SELECT end_time 
        FROM training_sessions 
        WHERE bank_code = %s AND status = 'completed'
        ORDER BY end_time DESC
        LIMIT 1
        """
        result = self.fetch_one(query, (bank_code,))
        return result['end_time'] if result else None
    
    def get_active_user_count(self, bank_code: str) -> int:
        """
        Obtiene el número de usuarios activos (últimas 24 horas) para un banco.
        
        Args:
            bank_code: Código del banco
            
        Returns:
            Número de usuarios activos
        """
        query = """
        SELECT COUNT(DISTINCT user_id) as count 
        FROM chatbot_sessions 
        WHERE bank_code = %s AND start_time > NOW() - INTERVAL '24 hours'
        """
        result = self.fetch_one(query, (bank_code,))
        return result['count'] if result else 0