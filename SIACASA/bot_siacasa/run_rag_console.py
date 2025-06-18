import os
import sys
from dotenv import load_dotenv

# Añadir el directorio raíz del proyecto al sys.path
# Esto es necesario para que los imports funcionen correctamente cuando se ejecuta este script
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from SIACASA.bot_siacasa.infrastructure.ai.llm_service import LLMService
from SIACASA.bot_siacasa.infrastructure.ai.vector_store_service import VectorStoreService
from SIACASA.bot_siacasa.application.use_cases.handle_user_query import HandleUserQuery

def main_console():
    """
    Punto de entrada para ejecutar el chatbot en modo consola con la nueva arquitectura RAG.
    """
    print("Iniciando SIACASA RAG Chatbot en modo consola...")
    
    # Cargar variables de entorno (buscará un archivo .env en el directorio actual o superior)
    load_dotenv()

    # --- Configuración de Dependencias ---
    
    # 1. Configurar el servicio de LLM
    try:
        llm_service = LLMService()
    except ValueError as e:
        print(f"Error: {e}")
        print("Asegúrate de tener un archivo .env en la raíz del proyecto con tu OPENAI_API_KEY.")
        return

    # 2. Configurar el servicio de Vector Store
    # La ruta al dataset es relativa a la ubicación de este script
    csv_path = os.path.join(project_root, 'SIACASA', 'datasets', 'dataset_v2_140.csv')
    try:
        vector_store_service = VectorStoreService(csv_path=csv_path)
    except FileNotFoundError as e:
        print(f"Error crítico: {e}")
        print("Asegúrate de que el archivo 'dataset_v2_140.csv' exista en la carpeta 'datasets'.")
        return
    except Exception as e:
        print(f"Error al inicializar el Vector Store: {e}")
        return

    # 3. Inyectar dependencias en el caso de uso
    handle_user_query_use_case = HandleUserQuery(
        llm_service=llm_service,
        vector_store_service=vector_store_service
    )

    print("\n--- Configuración completada. ¡Listo para chatear! ---")
    print("Escribe 'salir' para terminar la conversación.")

    # --- Bucle de Interacción ---
    while True:
        try:
            user_input = input("\nTú: ")
            if user_input.lower() in ['salir', 'exit', 'quit']:
                print("SIACASA: ¡Hasta luego!")
                break
            
            if not user_input.strip():
                continue

            # Ejecutar el caso de uso
            response = handle_user_query_use_case.execute(user_input)
            
            print(f"\nSIACASA:\n{response}")

        except KeyboardInterrupt:
            print("\nSIACASA: ¡Hasta luego!")
            break
        except Exception as e:
            print(f"\nOcurrió un error inesperado: {e}")
            # Podrías querer agregar más lógica de manejo de errores aquí
            break

if __name__ == "__main__":
    main_console() 