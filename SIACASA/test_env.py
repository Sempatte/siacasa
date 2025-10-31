# test_env.py
import os
from dotenv import load_dotenv
from pathlib import Path

# Intentar cargar desde diferentes rutas
print("🔍 Probando carga de variables de entorno...\n")

# Opción 1: Cargar .env desde el directorio actual
load_dotenv()
api_key_1 = os.getenv('OPENAI_API_KEY')
print(f"1. Carga básica: {'✓' if api_key_1 else '✗'}")
if api_key_1:
    print(f"   Primeros 10 caracteres: {api_key_1[:10]}...")
    print(f"   Longitud: {len(api_key_1)} caracteres")

# Opción 2: Especificar la ruta exacta
env_path = Path('.') / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    api_key_2 = os.getenv('OPENAI_API_KEY')
    print(f"\n2. Carga con ruta específica: {'✓' if api_key_2 else '✗'}")
    print(f"   Archivo .env encontrado en: {env_path.absolute()}")
else:
    print(f"\n2. ✗ No se encontró .env en: {env_path.absolute()}")

# Opción 3: Buscar en el directorio padre
parent_env = Path('..') / '.env'
if parent_env.exists():
    load_dotenv(dotenv_path=parent_env)
    api_key_3 = os.getenv('OPENAI_API_KEY')
    print(f"\n3. Carga desde directorio padre: {'✓' if api_key_3 else '✗'}")
    print(f"   Archivo .env encontrado en: {parent_env.absolute()}")

# Mostrar todas las variables de entorno que contengan "OPENAI"
print("\n📋 Variables de entorno relacionadas con OpenAI:")
for key, value in os.environ.items():
    if 'OPENAI' in key.upper():
        print(f"   {key}: {value[:10]}... (longitud: {len(value)})")

# Verificar permisos del archivo
if env_path.exists():
    print(f"\n📁 Información del archivo .env:")
    print(f"   Permisos: {oct(os.stat(env_path).st_mode)[-3:]}")
    print(f"   Tamaño: {os.stat(env_path).st_size} bytes")