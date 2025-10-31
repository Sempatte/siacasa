import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class KnowledgeBaseService:
    """
    Servicio encargado de recuperar fragmentos relevantes desde la base vectorial
    almacenada en NeonDB para enriquecer las respuestas del chatbot.
    """

    def __init__(
        self,
        db_connector,
        ai_provider,
        default_bank_code: str = "default",
        top_k: int = 3,
        min_similarity: float = 0.55
    ) -> None:
        self.db = db_connector
        self.ai_provider = ai_provider
        self.default_bank_code = default_bank_code
        self.top_k = top_k
        self.min_similarity = min_similarity

    def retrieve_context(
        self,
        query: str,
        bank_code: Optional[str] = None,
        top_k: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Recupera fragmentos relevantes para una consulta determinada.

        Args:
            query: Texto de la consulta del usuario.
            bank_code: Código de banco a filtrar (default si no se especifica).
            top_k: Número máximo de fragmentos a devolver.

        Returns:
            Lista de diccionarios con texto y similitud.
        """
        if not query or not query.strip():
            return []

        if not self.db or not self.ai_provider:
            logger.debug("KnowledgeBaseService inactivo: no hay DB o proveedor IA disponible.")
            return []

        embedding = self.ai_provider.generar_embedding(query)
        if not embedding:
            logger.debug("No se pudo generar embedding para la consulta.")
            return []

        embedding_str = f"[{','.join(map(str, embedding))}]"
        limit = top_k or self.top_k
        code = (bank_code or self.default_bank_code).lower()

        try:
            results = self.db.fetch_all(
                """
                SELECT 
                    text,
                    file_id,
                    bank_code,
                    1 - (embedding <=> %s::vector) AS similarity
                FROM text_embeddings
                WHERE bank_code = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (embedding_str, code, embedding_str, limit)
            )
        except Exception as e:
            logger.error(f"Error consultando text_embeddings: {e}", exc_info=True)
            return []

        filtered = [
            {
                "text": row.get("text", ""),
                "bank_code": row.get("bank_code"),
                "similarity": float(row.get("similarity", 0.0)),
                "file_id": row.get("file_id")
            }
            for row in (results or [])
            if float(row.get("similarity", 0.0)) >= self.min_similarity
        ]

        if filtered:
            logger.debug(
                "Contexto recuperado (%s resultados) para banco %s. Similitudes: %s",
                len(filtered),
                code,
                [f"{item['similarity']:.2f}" for item in filtered]
            )
            return filtered

        # Fallback a banco por defecto si no hay resultados y no estamos ya en default
        if code != self.default_bank_code:
            logger.info(
                "Sin resultados para bank_code=%s, intentando base por defecto %s.",
                code,
                self.default_bank_code
            )
            return self.retrieve_context(query, bank_code=self.default_bank_code, top_k=limit)

        return []
