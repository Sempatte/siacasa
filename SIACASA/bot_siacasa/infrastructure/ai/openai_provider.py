# bot_siacasa/infrastructure/ai/openai_provider.py
import json
import logging
from typing import Dict, List, Optional
import openai

from bot_siacasa.application.interfaces.ia_provider_interface import IAProviderInterface

logger = logging.getLogger(__name__)

class OpenAIProvider(IAProviderInterface):
    """
    Implementación del proveedor de IA utilizando la API de OpenAI.
    """
    
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """
        Inicializa el proveedor de OpenAI.
        
        Args:
            api_key: API key de OpenAI
            model: Modelo de OpenAI a utilizar
        """
        self.model = model
        openai.api_key = api_key
    
    def analizar_sentimiento(self, texto: str) -> Dict:
        """
        Analiza el sentimiento de un texto utilizando OpenAI.
        
        Args:
            texto: Texto a analizar
            
        Returns:
            Diccionario con información del sentimiento
        """
        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Eres un analizador de sentimientos. Debes analizar el texto proporcionado y devolver solo un JSON con los siguientes campos: sentimiento (positivo, negativo, neutral), confianza (valor de 0 a 1), emociones (lista de emociones detectadas)."},
                    {"role": "user", "content": f"Analiza el siguiente texto: {texto}"}
                ],
                response_format={"type": "json_object"}
            )
            
            # Extraer y procesar el resultado
            resultado_json = json.loads(response.choices[0].message.content)
            logger.info(f"Análisis de sentimiento completado: {resultado_json}")
            return resultado_json
        except Exception as e:
            logger.error(f"Error en el análisis de sentimiento: {e}")
            # Valor por defecto en caso de error
            return {
                "sentimiento": "neutral",
                "confianza": 0.5,
                "emociones": []
            }
    
    def generar_respuesta(self, mensajes: List[Dict[str, str]], instrucciones_adicionales: str = None) -> str:
        """
        Genera una respuesta utilizando OpenAI.
        
        Args:
            mensajes: Lista de mensajes en formato {role, content}
            instrucciones_adicionales: Instrucciones adicionales para la generación
            
        Returns:
            Texto de la respuesta generada
        """
        try:
            # Copiar los mensajes para no modificar el original
            mensajes_completos = mensajes.copy()
            
            # Agregar instrucciones adicionales si se proporcionan
            if instrucciones_adicionales:
                mensajes_completos.append({"role": "system", "content": instrucciones_adicionales})
            
            # Generar respuesta con el modelo
            response = openai.chat.completions.create(
                model=self.model,
                messages=mensajes_completos,
                max_tokens=500,
                temperature=0.7
            )
            
            # Extraer el texto de la respuesta
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error al generar respuesta: {e}")
            return "Lo siento, estoy experimentando problemas técnicos en este momento. ¿Podrías intentarlo de nuevo más tarde o contactar con nuestro servicio de atención al cliente?"