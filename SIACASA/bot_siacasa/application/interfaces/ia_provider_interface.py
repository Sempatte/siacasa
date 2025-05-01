# Revisa y corrige bot_siacasa/application/interfaces/ia_provider_interface.py
from abc import ABC, abstractmethod
from typing import Dict, List, Any

class IAProviderInterface(ABC):
    """
    Interfaz para proveedores de servicios de IA.
    Define los métodos que cualquier proveedor de IA debe implementar.
    """
    
    @abstractmethod
    def analizar_sentimiento(self, texto: str) -> Dict:
        """
        Analiza el sentimiento de un texto.
        
        Args:
            texto: Texto a analizar
            
        Returns:
            Diccionario con información del sentimiento
        """
        pass
    
    @abstractmethod
    def generar_respuesta(self, mensajes: List[Dict[str, str]], instrucciones_adicionales: str = None) -> str:
        """
        Genera una respuesta basada en una lista de mensajes.
        
        Args:
            mensajes: Lista de mensajes en formato {role, content}
            instrucciones_adicionales: Instrucciones adicionales para la generación
            
        Returns:
            Texto de la respuesta generada
        """
        pass