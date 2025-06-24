#!/usr/bin/env python3
"""
Script para inicializar el sistema de métricas SIACASA
"""
import os
import sys
from datetime import datetime, timedelta

# Añadir el directorio raíz del proyecto al sys.path
# Esto permite que el script encuentre el paquete bot_siacasa
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from bot_siacasa.metrics.database import init_database, reset_database
from bot_siacasa.metrics.collector import metrics_collector
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Función principal"""
    print("🚀 Inicializando sistema de métricas SIACASA...")
    
    try:
        # Crear tablas
        print("📊 Creando tablas de métricas...")
        init_database()
        print("✅ Tablas creadas exitosamente")
        
        # Verificar conexión
        print("🔍 Verificando conexión...")
        session_id = metrics_collector.get_or_create_session_for_user("test_user")
        print(f"✅ Conexión verificada - Sesión de prueba: {session_id}")
        
        print("\n🎉 Sistema de métricas inicializado correctamente!")
        print("\n📋 Próximos pasos:")
        print("1. Reinicia tu aplicación SIACASA")
        print("2. Las métricas se recopilarán automáticamente")
        print("3. Visita /api/metrics/health para verificar el estado")
        print("4. Usa /api/metrics/realtime-stats para estadísticas en vivo")
        
    except Exception as e:
        logger.error(f"Error inicializando métricas: {e}")
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())