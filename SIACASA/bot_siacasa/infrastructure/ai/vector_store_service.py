import pandas as pd
import faiss
import numpy as np
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.docstore.document import Document
import os

class VectorStoreService:
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.vector_store = None
        self._initialize_vector_store()

    def _initialize_vector_store(self):
        """
        Carga los datos, preprocesa el texto, genera embeddings y crea el vector store.
        """
        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(f"El archivo CSV no se encontró en la ruta: {self.csv_path}")

        # Cargar el dataset
        df = pd.read_csv(self.csv_path)

        # Verificar que el DataFrame tiene al menos dos columnas
        if len(df.columns) < 2:
            raise ValueError("El archivo CSV debe tener al menos dos columnas: una para la pregunta y otra para la respuesta.")

        # Usar los nombres de las dos primeras columnas dinámicamente
        question_col = df.columns[0]
        answer_col = df.columns[1]

        # Combinar pregunta y respuesta como fuente de conocimiento
        df['knowledge'] = f"Pregunta del cliente: " + df[question_col].astype(str) + \
                          f" | Respuesta del agente: " + df[answer_col].astype(str)
        
        # Crear documentos de LangChain
        documents = [Document(page_content=text) for text in df['knowledge'].tolist()]
        
        # Dividir documentos en chunks (aunque aquí cada interacción es un documento)
        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        docs = text_splitter.split_documents(documents)
        
        # Seleccionar el modelo de embeddings
        # 'paraphrase-multilingual-MiniLM-L12-v2' es un buen modelo para español.
        embeddings_model = HuggingFaceEmbeddings(
            model_name='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
        )
        
        # Crear el vector store con FAISS
        try:
            self.vector_store = FAISS.from_documents(docs, embeddings_model)
            print("Vector store creado exitosamente.")
        except Exception as e:
            print(f"Error al crear el vector store con FAISS: {e}")
            raise

    def search(self, query: str, k: int = 4) -> list[Document]:
        """
        Realiza una búsqueda de similitud en el vector store.
        
        Args:
            query (str): La consulta para buscar.
            k (int): El número de resultados a devolver.
            
        Returns:
            list[Document]: Una lista de los documentos más similares.
        """
        if not self.vector_store:
            raise Exception("El Vector Store no ha sido inicializado.")
            
        try:
            # Búsqueda de similitud
            similar_docs = self.vector_store.similarity_search(query, k=k)
            return similar_docs
        except Exception as e:
            print(f"Error durante la búsqueda de similitud: {e}")
            return []

# Ejemplo de uso (opcional, para pruebas)
if __name__ == '__main__':
    # La ruta debe ser relativa al directorio raíz del proyecto SIACASA
    # Suponiendo que este script se ejecuta desde SIACASA/bot_siacasa/infrastructure/ai
    ruta_dataset = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'datasets', 'dataset_v2_140.csv')

    if os.path.exists(ruta_dataset):
        vector_service = VectorStoreService(csv_path=ruta_dataset)
        
        # Prueba de búsqueda
        test_query = "información sobre crédito hipotecario"
        results = vector_service.search(test_query)
        
        print(f"\nResultados de la búsqueda para: '{test_query}'")
        for doc in results:
            print("---")
            print(doc.page_content)
    else:
        print(f"No se pudo encontrar el dataset en la ruta: {ruta_dataset}") 