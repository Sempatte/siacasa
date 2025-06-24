from SIACASA.bot_siacasa.infrastructure.ai.llm_service import LLMService
from SIACASA.bot_siacasa.infrastructure.ai.vector_store_service import VectorStoreService

class HandleUserQuery:
    def __init__(self, llm_service: LLMService, vector_store_service: VectorStoreService):
        """
        Inicializa el caso de uso con las dependencias necesarias.
        
        Args:
            llm_service: El servicio para interactuar con el modelo de lenguaje.
            vector_store_service: El servicio para buscar en la base de conocimiento vectorial.
        """
        self.llm_service = llm_service
        self.vector_store_service = vector_store_service

    def execute(self, user_query: str) -> str:
        """
        Orquesta el flujo completo para manejar la consulta de un usuario.
        
        1. Analiza la consulta del usuario.
        2. Busca en la base de conocimiento.
        3. Genera una respuesta final.
        
        Args:
            user_query: La consulta textual del usuario.
            
        Returns:
            La respuesta generada por el sistema.
        """
        # 1. Analizar la consulta del usuario en tiempo real
        print(f"Analizando consulta: '{user_query}'")
        query_analysis = self.llm_service.analyze_query(user_query)
        print(f"Análisis completado: Sentimiento='{query_analysis.sentiment}', Tono='{query_analysis.response_tone}'")
        print(f"Entidades detectadas: {query_analysis.detected_entities}")
        print(f"Consulta para búsqueda: '{query_analysis.cleaned_query}'")

        # 2. Buscar en la base de conocimiento usando la consulta limpia
        retrieved_docs = self.vector_store_service.search(query_analysis.cleaned_query, k=3)
        
        if not retrieved_docs:
            # Fallback si no se encuentran documentos
            return "Lo siento, no pude encontrar información relevante sobre tu consulta. ¿Podrías reformular tu pregunta o te gustaría hablar con un agente humano?"
            
        # 3. Preparar el contexto para la generación de la respuesta
        context = "\n\n---\n\n".join([doc.page_content for doc in retrieved_docs])
        print(f"Contexto recuperado para la respuesta:\n{context}")

        # 4. Generar la respuesta final
        final_response = self.llm_service.generate_response(query_analysis, context)
        print(f"Respuesta final generada:\n{final_response}")
        
        return final_response 