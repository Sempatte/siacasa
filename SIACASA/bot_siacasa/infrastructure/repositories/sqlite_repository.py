# Nuevo archivo: bot_siacasa/infrastructure/repositories/sqlite_repository.py
import sqlite3
import json
import pickle
from datetime import datetime
from typing import Dict, Optional, List

from bot_siacasa.application.interfaces.repository_interface import IRepository
from bot_siacasa.domain.entities.usuario import Usuario
from bot_siacasa.domain.entities.conversacion import Conversacion

class SQLiteRepository(IRepository):
    """Implementación de repositorio utilizando SQLite."""
    
    def __init__(self, db_path="./chatbot_data.db"):
        """Inicializa el repositorio con la ruta a la base de datos."""
        self.db_path = db_path
        self._crear_tablas()
    
    def _crear_tablas(self):
        """Crea las tablas necesarias si no existen."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabla de usuarios
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id TEXT PRIMARY KEY,
            datos TEXT,
            fecha_creacion TEXT
        )
        ''')
        
        # Tabla de conversaciones
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversaciones (
            id TEXT PRIMARY KEY,
            usuario_id TEXT,
            fecha_inicio TEXT,
            fecha_fin TEXT,
            activa INTEGER,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
        ''')
        
        # Tabla de mensajes
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS mensajes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversacion_id TEXT,
            role TEXT,
            content TEXT,
            timestamp TEXT,
            FOREIGN KEY (conversacion_id) REFERENCES conversaciones (id)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    # Implementa los métodos de la interfaz IRepository...