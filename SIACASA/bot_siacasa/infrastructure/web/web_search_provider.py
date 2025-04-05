# bot_siacasa/infrastructure/web/web_search_provider.py
import requests
import logging
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class WebSearchProvider:
    """
    Proveedor de búsqueda web que permite al chatbot acceder a información en internet.
    """
    
    def __init__(self, search_api_key: Optional[str] = None):
        """
        Inicializa el proveedor de búsqueda web.
        
        Args:
            search_api_key: Clave de API para el servicio de búsqueda (opcional)
        """
        self.search_api_key = search_api_key
    
    def search(self, query: str, num_results: int = 3) -> List[Dict]:
        """
        Realiza una búsqueda web basada en una consulta.
        
        Args:
            query: Consulta de búsqueda
            num_results: Número de resultados a devolver
            
        Returns:
            Lista de resultados con título, URL y snippet
        """
        try:
            # Esta es una implementación simple. En producción, considera usar
            # un servicio como Google Custom Search API, Bing Search API, etc.
            
            # Ejemplo usando Duck Duck Go (no requiere API key)
            url = f"https://lite.duckduckgo.com/lite/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            params = {
                'q': query
            }
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            # Parsear los resultados
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Extracción básica de resultados de DuckDuckGo Lite
            # Nota: Esta implementación es simplificada y podría necesitar ajustes
            for i, result in enumerate(soup.find_all('a', {'class': 'result-link'})):
                if i >= num_results:
                    break
                    
                title = result.text.strip()
                link = result['href']
                
                # Intentar encontrar el snippet
                snippet_elem = result.find_next('td', {'class': 'result-snippet'})
                snippet = snippet_elem.text.strip() if snippet_elem else ""
                
                results.append({
                    'title': title,
                    'url': link,
                    'snippet': snippet
                })
            
            logger.info(f"Búsqueda web completada para: {query}. Resultados encontrados: {len(results)}")
            return results
            
        except Exception as e:
            logger.error(f"Error en búsqueda web: {e}")
            return []
    
    def fetch_content(self, url: str) -> Optional[str]:
        """
        Obtiene el contenido de una URL.
        
        Args:
            url: URL de la página a obtener
            
        Returns:
            Texto extraído de la página o None si hay error
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Extraer el texto de la página
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Eliminar elementos no deseados
            for element in soup(['script', 'style', 'header', 'footer', 'nav']):
                element.extract()
            
            # Obtener el texto
            text = soup.get_text(separator=' ', strip=True)
            
            # Limpiar el texto (eliminar espacios múltiples, etc.)
            import re
            text = re.sub(r'\s+', ' ', text).strip()
            
            return text
            
        except Exception as e:
            logger.error(f"Error al obtener contenido de {url}: {e}")
            return None