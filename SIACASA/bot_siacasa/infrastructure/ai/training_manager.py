# bot_siacasa/infrastructure/ai/training_manager.py
import logging
import os
import uuid
import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import openai
from openai import OpenAI
import pandas as pd
import docx
import PyPDF2
import csv
import markdown
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class TrainingManager:
    """
    Gestor de entrenamiento del chatbot con archivos proporcionados por el banco.
    """
    
    def __init__(self, db_connector):
        """
        Inicializa el gestor de entrenamiento.
        
        Args:
            db_connector: Conector a la base de datos
        """
        self.db = db_connector
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.upload_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'uploads', 'training')
        
        # Crear carpeta de uploads si no existe
        os.makedirs(self.upload_folder, exist_ok=True)
    
    def process_training_file(self, file_id: str) -> Tuple[bool, str]:
        """
        Procesa un archivo de entrenamiento.
        
        Args:
            file_id: ID del archivo a procesar
            
        Returns:
            Tupla con el estado (éxito/error) y mensaje
        """
        try:
            # Obtener información del archivo
            query = """
            SELECT id, filename, original_filename, file_path, file_type, bank_code 
            FROM training_files 
            WHERE id = %s
            """
            file_info = self.db.fetch_one(query, (file_id,))
            
            if not file_info:
                return False, "Archivo no encontrado"
            
            # Actualizar estado del archivo
            self.db.execute(
                "UPDATE training_files SET status = 'processing' WHERE id = %s",
                (file_id,)
            )
            
            # Extraer texto del archivo según su tipo
            file_path = os.path.join(self.upload_folder, file_info['filename'])
            file_text = self._extract_text_from_file(file_path, file_info['file_type'])
            
            if not file_text:
                self.db.execute(
                    "UPDATE training_files SET status = 'error', processed_at = %s WHERE id = %s",
                    (datetime.now(), file_id)
                )
                return False, "No se pudo extraer texto del archivo"
            
            # Convertir el texto en embeddings y guardar en vector database
            success = self._create_embeddings(file_text, file_info)
            
            if success:
                # Actualizar estado del archivo
                self.db.execute(
                    "UPDATE training_files SET status = 'completed', processed_at = %s WHERE id = %s",
                    (datetime.now(), file_id)
                )
                return True, "Archivo procesado correctamente"
            else:
                # Actualizar estado del archivo
                self.db.execute(
                    "UPDATE training_files SET status = 'error', processed_at = %s WHERE id = %s",
                    (datetime.now(), file_id)
                )
                return False, "Error al crear embeddings"
                
        except Exception as e:
            logger.error(f"Error al procesar archivo de entrenamiento {file_id}: {e}", exc_info=True)
            
            # Actualizar estado del archivo
            try:
                self.db.execute(
                    "UPDATE training_files SET status = 'error', processed_at = %s WHERE id = %s",
                    (datetime.now(), file_id)
                )
            except Exception:
                pass
                
            return False, f"Error: {str(e)}"
    
    def _extract_text_from_file(self, file_path: str, file_type: str) -> Optional[str]:
        """
        Extrae texto de un archivo según su tipo.
        
        Args:
            file_path: Ruta al archivo
            file_type: Tipo de archivo
            
        Returns:
            Texto extraído o None si hay error
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"El archivo no existe: {file_path}")
                return None
                
            file_type = file_type.lower()
            
            # Texto plano
            if file_type in ['txt', 'text/plain']:
                with open(file_path, 'r', encoding='utf-8') as file:
                    return file.read()
            
            # PDF
            elif file_type in ['pdf', 'application/pdf']:
                text = ""
                with open(file_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                return text
            
            # Word
            elif file_type in ['doc', 'docx', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                doc = docx.Document(file_path)
                return "\n".join([para.text for para in doc.paragraphs])
            
            # CSV
            elif file_type in ['csv', 'text/csv']:
                text = ""
                with open(file_path, 'r', encoding='utf-8') as file:
                    reader = csv.reader(file)
                    headers = next(reader)
                    text += ", ".join(headers) + "\n"
                    for row in reader:
                        text += ", ".join(row) + "\n"
                return text
            
            # Excel
            elif file_type in ['xls', 'xlsx', 'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']:
                df = pd.read_excel(file_path)
                return df.to_string()
            
            # JSON
            elif file_type in ['json', 'application/json']:
                with open(file_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                return json.dumps(data, indent=2)
            
            # Markdown
            elif file_type in ['md', 'markdown', 'text/markdown']:
                with open(file_path, 'r', encoding='utf-8') as file:
                    return file.read()
            
            # HTML
            elif file_type in ['html', 'htm', 'text/html']:
                with open(file_path, 'r', encoding='utf-8') as file:
                    soup = BeautifulSoup(file.read(), 'html.parser')
                    return soup.get_text()
            
            else:
                logger.warning(f"Tipo de archivo no soportado: {file_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error al extraer texto del archivo {file_path}: {e}", exc_info=True)
            return None
    
    def _create_embeddings(self, text: str, file_info: Dict[str, Any]) -> bool:
        """
        Crea embeddings a partir del texto y los guarda en la base de datos.
        
        Args:
            text: Texto a procesar
            file_info: Información del archivo
            
        Returns:
            True si se crearon correctamente, False en caso contrario
        """
        try:
            # Dividir el texto en chunks para procesar (máximo 8000 tokens por chunk)
            chunks = self._split_into_chunks(text)
            
            for i, chunk in enumerate(chunks):
                # Crear embedding usando OpenAI
                embedding = self._get_embedding(chunk)
                
                if embedding:
                    # Guardar embedding en la base de datos
                    self._save_embedding(embedding, chunk, file_info, i)
                    
                    # Pequeña pausa para no exceder límites de API
                    time.sleep(0.5)
                else:
                    logger.warning(f"No se pudo crear embedding para el chunk {i}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error al crear embeddings: {e}", exc_info=True)
            return False
    
    def _split_into_chunks(self, text: str, max_tokens: int = 8000) -> List[str]:
        """
        Divide un texto en chunks más pequeños.
        
        Args:
            text: Texto a dividir
            max_tokens: Número máximo de tokens por chunk
            
        Returns:
            Lista de chunks
        """
        # Estimación simple: cada palabra son aproximadamente 1.3 tokens
        words = text.split()
        total_words = len(words)
        words_per_chunk = int(max_tokens / 1.3)
        
        chunks = []
        for i in range(0, total_words, words_per_chunk):
            chunk = " ".join(words[i:i + words_per_chunk])
            chunks.append(chunk)
        
        return chunks
    
    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Obtiene el embedding de un texto usando OpenAI.
        
        Args:
            text: Texto a procesar
            
        Returns:
            Vector de embedding o None si hay error
        """
        try:
            # Usar modelo de embeddings de OpenAI
            response = self.client.embeddings.create(
                input=text,
                model="text-embedding-3-small"
            )
            
            # Extraer el vector de embedding
            embedding = response.data[0].embedding
            return embedding
            
        except Exception as e:
            logger.error(f"Error al obtener embedding: {e}", exc_info=True)
            return None
    
    def _save_embedding(self, embedding: List[float], text: str, file_info: Dict[str, Any], chunk_index: int) -> None:
        """
        Guarda un embedding en la base de datos.
        
        Args:
            embedding: Vector de embedding
            text: Texto original
            file_info: Información del archivo
            chunk_index: Índice del chunk
        """
        try:
            # Crear tabla de embeddings si no existe
            self.db.execute("""
            CREATE TABLE IF NOT EXISTS text_embeddings (
                id UUID PRIMARY KEY,
                file_id UUID REFERENCES training_files(id),
                bank_code VARCHAR(10) REFERENCES banks(code),
                chunk_index INTEGER,
                text TEXT,
                embedding VECTOR(1536),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # Insertar embedding en la base de datos
            query = """
            INSERT INTO text_embeddings (id, file_id, bank_code, chunk_index, text, embedding)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            embedding_id = str(uuid.uuid4())
            
            # Convertir la lista de embeddings a formato de vector PostgreSQL
            embedding_str = f"[{','.join(map(str, embedding))}]"
            
            self.db.execute(
                query,
                (
                    embedding_id,
                    file_info['id'],
                    file_info['bank_code'],
                    chunk_index,
                    text,
                    embedding_str
                )
            )
            
        except Exception as e:
            logger.error(f"Error al guardar embedding: {e}", exc_info=True)
            raise
    
    def start_training_session(self, bank_code: str, user_id: str, file_ids: List[str]) -> str:
        """
        Inicia una sesión de entrenamiento para procesar varios archivos.
        
        Args:
            bank_code: Código del banco
            user_id: ID del usuario que inicia el entrenamiento
            file_ids: Lista de IDs de archivos a procesar
            
        Returns:
            ID de la sesión de entrenamiento
        """
        try:
            # Crear registro de sesión de entrenamiento
            session_id = str(uuid.uuid4())
            
            query = """
            INSERT INTO training_sessions (
                id, bank_code, initiated_by, status, files_count, start_time
            )
            VALUES (%s, %s, %s, 'processing', %s, %s)
            """
            
            self.db.execute(
                query,
                (session_id, bank_code, user_id, len(file_ids), datetime.now())
            )
            
            # Asociar archivos con la sesión
            for file_id in file_ids:
                self.db.execute(
                    """
                    INSERT INTO training_session_files (session_id, file_id, status)
                    VALUES (%s, %s, 'pending')
                    """,
                    (session_id, file_id)
                )
            
            # Procesar archivos (en un proceso separado en una aplicación real)
            for file_id in file_ids:
                success, message = self.process_training_file(file_id)
                
                status = 'completed' if success else 'error'
                
                # Actualizar estado del archivo en la sesión
                self.db.execute(
                    """
                    UPDATE training_session_files 
                    SET status = %s, error_message = %s, processed_at = %s
                    WHERE session_id = %s AND file_id = %s
                    """,
                    (status, None if success else message, datetime.now(), session_id, file_id)
                )
                
                # Actualizar contadores en la sesión
                if success:
                    self.db.execute(
                        "UPDATE training_sessions SET success_count = success_count + 1 WHERE id = %s",
                        (session_id,)
                    )
                else:
                    self.db.execute(
                        "UPDATE training_sessions SET error_count = error_count + 1 WHERE id = %s",
                        (session_id,)
                    )
            
            # Actualizar estado de la sesión
            self.db.execute(
                """
                UPDATE training_sessions 
                SET status = 'completed', end_time = %s
                WHERE id = %s
                """,
                (datetime.now(), session_id)
            )
            
            return session_id
            
        except Exception as e:
            logger.error(f"Error al iniciar sesión de entrenamiento: {e}", exc_info=True)
            
            # Actualizar estado de la sesión si se creó
            if 'session_id' in locals():
                try:
                    self.db.execute(
                        """
                        UPDATE training_sessions 
                        SET status = 'error', end_time = %s
                        WHERE id = %s
                        """,
                        (datetime.now(), session_id)
                    )
                except Exception:
                    pass
            
            raise