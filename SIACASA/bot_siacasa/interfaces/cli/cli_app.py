# bot_siacasa/interfaces/cli/cli_app.py
import uuid
import logging
from typing import Optional

from bot_siacasa.application.use_cases.procesar_mensaje_use_case import ProcesarMensajeUseCase

logger = logging.getLogger(__name__)

class CLIApp:
    """
    Aplicación de línea de comandos para interactuar con el chatbot.
    """
    
    def __init__(self, procesar_mensaje_use_case: ProcesarMensajeUseCase):
        """
        Inicializa la aplicación CLI.
        
        Args:
            procesar_mensaje_use_case: Caso de uso para procesar mensajes
        """
        self.procesar_mensaje_use_case = procesar_mensaje_use_case
        self.usuario_id = str(uuid.uuid4())
    
    def run(self) -> None:
        """
        Ejecuta la aplicación CLI.
        """
        print("\n=================================")
        print("    SIACASA - Chatbot Bancario   ")
        print("=================================\n")
        print("Bienvenido a SIACASA, tu asistente bancario virtual.")
        print("Escribe 'salir' para terminar la conversación.\n")
        
        # Mensaje de bienvenida automático
        self._mostrar_respuesta("¡Hola! Soy SIACASA, tu asistente bancario virtual. ¿En qué puedo ayudarte hoy?")
        
        while True:
            try:
                # Solicitar entrada del usuario
                mensaje_usuario = input("\nTú: ")
                
                # Verificar si el usuario quiere salir
                if mensaje_usuario.lower() in ["salir", "exit", "quit", "terminar"]:
                    print("\nGracias por utilizar SIACASA. ¡Hasta pronto!")
                    break
                
                # Procesar el mensaje y obtener la respuesta
                respuesta = self.procesar_mensaje_use_case.execute(
                    mensaje_usuario=mensaje_usuario,
                    usuario_id=self.usuario_id
                )
                
                # Mostrar la respuesta
                self._mostrar_respuesta(respuesta)
                
            except KeyboardInterrupt:
                print("\n\nOperación interrumpida. Saliendo...")
                break
            except Exception as e:
                logger.error(f"Error en la aplicación CLI: {e}")
                print("\nLo siento, ocurrió un error inesperado. Por favor, inténtalo de nuevo.")
    
    def _mostrar_respuesta(self, respuesta: str) -> None:
        """
        Muestra una respuesta del chatbot en la consola.
        
        Args:
            respuesta: Texto de la respuesta
        """
        print(f"\nSIACASA: {respuesta}")