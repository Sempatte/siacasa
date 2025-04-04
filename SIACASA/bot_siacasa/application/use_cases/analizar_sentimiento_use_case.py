import logging
from typing import Dict

from bot_siacasa.application.interfaces.ia_provider_interface import IAProviderInterface
from bot_siacasa.domain.entities.analisis_sentimiento import AnalisisSentimiento

logger = logging.getLogger(__name__)

class AnalizarSentimientoUseCase:
    """
    Caso de uso para analizar el sentimiento de un texto.
    """
    
    def __init__(self, ia_provider: IAProviderInterface):
        """
        Inicializa el caso de uso.
        
        Args:
            ia_provider: Proveedor de IA para análisis de sentimientos
        """
        self.ia_provider = ia_provider
    
    def execute(self, texto: str) -> AnalisisSentimiento:
        """
        Ejecuta el análisis de sentimiento.
        
        Args:
            texto: Texto a analizar
            
        Returns:
            AnalisisSentimiento con el resultado del análisis
        """
        try:
            # Analizar sentimiento usando el proveedor de IA
            resultado = self.ia_provider.analizar_sentimiento(texto)
            
            # Crear y devolver objeto de dominio
            return AnalisisSentimiento(
                sentimiento=resultado.get("sentimiento", "neutral"),
                confianza=resultado.get("confianza", 0.5),
                emociones=resultado.get("emociones", []),
                metadata=resultado.get("metadata")
            )
        except Exception as e:
            logger.error(f"Error al analizar sentimiento: {e}")
            # Devolver valor por defecto en caso de error
            return AnalisisSentimiento.default()