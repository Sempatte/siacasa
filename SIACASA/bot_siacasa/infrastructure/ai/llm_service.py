import os
import json
from openai import OpenAI
from SIACASA.bot_siacasa.domain.entities.query_analysis import QueryAnalysis

class LLMService:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        if not self.client.api_key:
            raise ValueError("La variable de entorno OPENAI_API_KEY no está configurada.")

    def analyze_query(self, query: str) -> QueryAnalysis:
        """
        Analiza la consulta de un usuario utilizando GPT-4o para extraer sentimiento,
        entidades, y generar una versión limpia de la consulta y un tono de respuesta.
        """
        prompt = f"""
        Analiza la siguiente consulta de un cliente de un banco rural en Perú. La consulta es: '{query}'

        Tu tarea es realizar un análisis completo y devolver un objeto JSON con la siguiente estructura:
        {{
          "sentiment": "...",           // Analiza el sentimiento (positivo, negativo, neutral).
          "detected_entities": {{...}}, // Identifica entidades clave como producto, monto, número de cuenta, etc.
          "cleaned_query": "...",       // Reformula la consulta para que sea clara y directa para una búsqueda semántica.
          "response_tone": "..."        // Sugiere un tono para la respuesta (ej. "formal y directo", "empático y tranquilizador").
        }}

        Considera la jerga y regionalismos peruanos. Por ejemplo, "plata" o "lana" significa dinero.
        Sé preciso y conciso en tu análisis.

        Ejemplo de respuesta para la consulta "hola, quiero saber sobre el crédito agrario, necesito 10 mil soles":
        {{
          "sentiment": "neutral",
          "detected_entities": {{
            "producto": "crédito agrario",
            "monto": "10000",
            "moneda": "soles"
          }},
          "cleaned_query": "Información sobre el crédito agrario de 10,000 soles.",
          "response_tone": "informativo y amigable"
        }}
        
        JSON a generar:
        """

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres un experto en NLU y análisis de sentimientos para el contexto bancario rural peruano."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )

        try:
            analysis_data = json.loads(response.choices[0].message.content)
            return QueryAnalysis(
                original_query=query,
                sentiment=analysis_data.get("sentiment", "neutral"),
                detected_entities=analysis_data.get("detected_entities", {}),
                cleaned_query=analysis_data.get("cleaned_query", query),
                response_tone=analysis_data.get("response_tone", "neutral")
            )
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error al procesar la respuesta del LLM: {e}")
            # Fallback a un análisis simple si el LLM falla
            return QueryAnalysis(
                original_query=query,
                sentiment="neutral",
                detected_entities={},
                cleaned_query=query,
                response_tone="neutral"
            )

    def generate_response(self, analysis: QueryAnalysis, context: str) -> str:
        """
        Genera una respuesta final para el usuario basada en el análisis de su consulta y el contexto recuperado.
        """
        prompt = f"""
        Eres un asistente virtual de SIACASA, un banco rural en Perú.
        Tu tono de respuesta debe ser: {analysis.response_tone}.
        
        La consulta original del cliente fue: "{analysis.original_query}"
        Las entidades detectadas en la consulta fueron: {analysis.detected_entities}
        
        La información recuperada de nuestra base de conocimiento es:
        ---
        {context}
        ---

        Basándote en la información recuperada, redacta una respuesta clara, concisa y útil para el cliente.
        Si la información no es suficiente para responder completamente, indícalo amablemente y sugiere escalar el caso a un agente humano.
        No inventes información. Dirígete al cliente de manera respetuosa y amigable.
        """

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres un asistente virtual de SIACASA, un banco rural en Perú."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            stream=False
        )

        return response.choices[0].message.content 