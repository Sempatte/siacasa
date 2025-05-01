# admin_panel/training/training_service.py
import os
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

class TrainingService:
    """
    Servicio para la gestión de archivos de entrenamiento.
    """
    
    def __init__(self, db_connector):
        """
        Inicializa el servicio de entrenamiento.
        
        Args:
            db_connector: Conector a la base de datos
        """
        self.db = db_connector
        self.upload_folder = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
            'uploads', 
            'training'
        )
        
        # Crear carpeta de uploads si no existe
        os.makedirs(self.upload_folder, exist_ok=True)
    
    def get_training_files(self, bank_code: str) -> List[Dict[str, Any]]:
        """
        Obtiene la lista de archivos de entrenamiento para un banco.
        
        Args:
            bank_code: Código del banco
            
        Returns:
            Lista de archivos de entrenamiento
        """
        query = """
        SELECT 
            tf.id, 
            tf.original_filename,
            tf.file_type,
            tf.file_size,
            tf.status,
            tf.description,
            tf.uploaded_at,
            tf.processed_at,
            au.name as uploaded_by_name
        FROM 
            training_files tf
        LEFT JOIN 
            admin_users au ON tf.uploaded_by = au.id
        WHERE 
            tf.bank_code = %s
        ORDER BY 
            tf.uploaded_at DESC
        """
        
        return self.db.fetch_all(query, (bank_code,))
    
    def get_training_history(self, bank_code: str) -> List[Dict[str, Any]]:
        """
        Obtiene el historial de entrenamientos para un banco.
        
        Args:
            bank_code: Código del banco
            
        Returns:
            Lista de sesiones de entrenamiento
        """
        query = """
        SELECT 
            ts.id,
            ts.status,
            ts.files_count,
            ts.success_count,
            ts.error_count,
            ts.start_time,
            ts.end_time,
            au.name as initiated_by_name
        FROM 
            training_sessions ts
        LEFT JOIN 
            admin_users au ON ts.initiated_by = au.id
        WHERE 
            ts.bank_code = %s
        ORDER BY 
            ts.start_time DESC
        LIMIT 10
        """
        
        return self.db.fetch_all(query, (bank_code,))
    
    def save_training_file(self, file, description: str, user_id: str, bank_code: str) -> Dict[str, Any]:
        """
        Guarda un archivo de entrenamiento.
        
        Args:
            file: Archivo a guardar
            description: Descripción del archivo
            user_id: ID del usuario que sube el archivo
            bank_code: Código del banco
            
        Returns:
            Información del archivo guardado
        """
        try:
            # Generar nombre seguro para el archivo
            original_filename = file.filename
            file_extension = os.path.splitext(original_filename)[1]
            secure_name = str(uuid.uuid4()) + file_extension
            file_path = os.path.join(self.upload_folder, secure_name)
            
            # Determinar tipo de archivo
            file_type = file.content_type or file_extension.replace('.', '')
            
            # Guardar archivo
            file.save(file_path)
            file_size = os.path.getsize(file_path)
            
            # Insertar en base de datos
            file_id = str(uuid.uuid4())
            query = """
            INSERT INTO training_files (
                id, 
                filename, 
                original_filename, 
                file_path, 
                file_type, 
                file_size, 
                bank_code, 
                uploaded_by, 
                description, 
                uploaded_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """
            
            self.db.execute(
                query,
                (
                    file_id,
                    secure_name,
                    original_filename,
                    file_path,
                    file_type,
                    file_size,
                    bank_code,
                    user_id,
                    description,
                    datetime.now()
                )
            )
            
            # Devolver información del archivo
            return {
                'id': file_id,
                'original_filename': original_filename,
                'file_type': file_type,
                'file_size': file_size,
                'status': 'pending',
                'description': description,
                'uploaded_at': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error al guardar archivo de entrenamiento: {e}", exc_info=True)
            raise
    
    def get_file_details(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene los detalles de un archivo de entrenamiento.
        
        Args:
            file_id: ID del archivo
            
        Returns:
            Detalles del archivo o None si no existe
        """
        query = """
        SELECT 
            tf.id, 
            tf.original_filename,
            tf.file_type,
            tf.file_size,
            tf.status,
            tf.description,
            tf.uploaded_at,
            tf.processed_at,
            tf.bank_code,
            au.name as uploaded_by_name
        FROM 
            training_files tf
        LEFT JOIN 
            admin_users au ON tf.uploaded_by = au.id
        WHERE 
            tf.id = %s
        """
        
        return self.db.fetch_one(query, (file_id,))
    
    def delete_file(self, file_id: str) -> bool:
        """
        Elimina un archivo de entrenamiento.

        Args:
            file_id: ID del archivo
            
        Returns:
            True si se eliminó correctamente, False en caso contrario
        """
        try:
            # Obtener información del archivo
            file_info = self.get_file_details(file_id)
            
            if not file_info:
                return False
            
            # Intentar eliminar archivo físico
            if 'filename' in file_info:
                file_path = os.path.join(self.upload_folder, file_info['filename'])
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except (PermissionError, OSError) as e:
                    # Registrar el error pero continuar con la eliminación en la base de datos
                    logger.warning(f"No se pudo eliminar el archivo físico: {e}")
            
            # Eliminar registro de la base de datos
            self.db.execute("DELETE FROM training_session_files WHERE file_id = %s", (file_id,))
            self.db.execute("DELETE FROM training_files WHERE id = %s", (file_id,))
            
            return True
            
        except Exception as e:
            logger.error(f"Error al eliminar archivo {file_id}: {e}", exc_info=True)
            return False
    def start_training(self, file_ids: List[str], user_id: str, bank_code: str) -> str:
        """
        Inicia un entrenamiento con los archivos seleccionados.
        
        Args:
            file_ids: Lista de IDs de archivos a procesar
            user_id: ID del usuario que inicia el entrenamiento
            bank_code: Código del banco
            
        Returns:
            ID de la sesión de entrenamiento
        """
        from bot_siacasa.infrastructure.ai.training_manager import TrainingManager
        
        training_manager = TrainingManager(self.db)
        session_id = training_manager.start_training_session(bank_code, user_id, file_ids)
        
        return session_id
    
    def get_training_session_details(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene los detalles de una sesión de entrenamiento.
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            Detalles de la sesión o None si no existe
        """
        # Obtener información básica de la sesión
        query = """
        SELECT 
            ts.id,
            ts.bank_code,
            ts.status,
            ts.files_count,
            ts.success_count,
            ts.error_count,
            ts.start_time,
            ts.end_time,
            ts.log_file,
            ts.results,
            au.name as initiated_by_name
        FROM 
            training_sessions ts
        LEFT JOIN 
            admin_users au ON ts.initiated_by = au.id
        WHERE 
            ts.id = %s
        """
        
        session = self.db.fetch_one(query, (session_id,))
        
        if not session:
            return None
        
        # Obtener archivos asociados a la sesión
        query = """
        SELECT 
            tf.id,
            tf.original_filename,
            tf.file_type,
            tsf.status,
            tsf.error_message,
            tsf.processed_at
        FROM 
            training_session_files tsf
        JOIN 
            training_files tf ON tsf.file_id = tf.id
        WHERE 
            tsf.session_id = %s
        """
        
        files = self.db.fetch_all(query, (session_id,))
        
        # Combinar información
        session['files'] = files
        
        return session