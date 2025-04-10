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
            # CAMBIO 1: Validar que los mensajes tengan el formato correcto
            mensajes_validados = []
            for msg in mensajes:
                if not isinstance(msg, dict) or 'role' not in msg or 'content' not in msg:
                    logger.warning(f"Mensaje con formato incorrecto ignorado: {msg}")
                    continue
                
                # Asegurar que el rol sea válido
                if msg['role'] not in ["system", "user", "assistant"]:
                    logger.warning(f"Mensaje con rol inválido ignorado: {msg['role']}")
                    continue
                    
                mensajes_validados.append(msg)
            
            # Si no hay mensajes válidos, crear uno de sistema básico
            if not mensajes_validados:
                logger.warning("No se encontraron mensajes válidos, usando mensaje de sistema por defecto")
                mensajes_validados = [{
                    "role": "system",
                    "content": "Eres un asistente bancario virtual. Por favor, ayuda al usuario."
                }]
            
            # CAMBIO 2: Mejorar la gestión de instrucciones adicionales
            if instrucciones_adicionales:
                # Buscar si ya existe un mensaje de sistema
                sistema_existente = False
                for msg in mensajes_validados:
                    if msg['role'] == 'system':
                        # Actualizar el contenido del mensaje de sistema existente
                        # concatenando las instrucciones adicionales
                        msg['content'] += "\n\n" + instrucciones_adicionales
                        sistema_existente = True
                        break
                
                # Si no hay mensaje de sistema, agregar uno nuevo
                if not sistema_existente:
                    mensajes_validados.insert(0, {
                        "role": "system",
                        "content": instrucciones_adicionales
                    })
            
            # CAMBIO 3: Mejorar el logging
            logger.info(f"Enviando {len(mensajes_validados)} mensajes a OpenAI:")
            for i, msg in enumerate(mensajes_validados[:3]):  # Solo los primeros 3 para el log
                role = msg['role']
                content_preview = msg['content'][:50] + "..." if len(msg['content']) > 50 else msg['content']
                logger.info(f"  Mensaje #{i}: {role} - {content_preview}")
            
            # CAMBIO 4: Ajustar parámetros para mejor contexto
            response = openai.chat.completions.create(
                model=self.model,
                messages=mensajes_validados,
                max_tokens=800,
                temperature=0.7,
                presence_penalty=0.8,  # Aumentado para dar más importancia al contexto
                frequency_penalty=0.5   # Añadido para evitar repeticiones
            )
            
            # Extraer el texto de la respuesta
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error al generar respuesta: {e}", exc_info=True)
            return "Lo siento, estoy experimentando problemas técnicos en este momento. ¿Podrías intentarlo de nuevo más tarde?"
