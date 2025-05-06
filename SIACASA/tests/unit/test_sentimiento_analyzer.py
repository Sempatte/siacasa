# tests/unit/test_sentimiento_analyzer.py
import pytest
from unittest.mock import Mock, patch

from bot_siacasa.domain.entities.analisis_sentimiento import AnalisisSentimiento
from bot_siacasa.application.use_cases.analizar_sentimiento_use_case import AnalizarSentimientoUseCase
from bot_siacasa.application.interfaces.ia_provider_interface import IAProviderInterface

class TestAnalizarSentimientoUseCase:
    """Tests para el caso de uso de análisis de sentimiento."""
    
    def test_execute_success(self):
        """Test del análisis de sentimiento exitoso."""
        # Arrange
        mock_provider = Mock(spec=IAProviderInterface)
        mock_provider.analizar_sentimiento.return_value = {
            "sentimiento": "positivo",
            "confianza": 0.85,
            "emociones": ["felicidad", "satisfacción"]
        }
        
        use_case = AnalizarSentimientoUseCase(mock_provider)
        
        # Act
        resultado = use_case.execute("Estoy muy contento con el servicio")
        
        # Assert
        assert isinstance(resultado, AnalisisSentimiento)
        assert resultado.sentimiento == "positivo"
        assert resultado.confianza == 0.85
        assert "felicidad" in resultado.emociones
        assert "satisfacción" in resultado.emociones
        mock_provider.analizar_sentimiento.assert_called_once_with("Estoy muy contento con el servicio")
    
    def test_execute_error(self):
        """Test del comportamiento ante un error."""
        # Arrange
        mock_provider = Mock(spec=IAProviderInterface)
        mock_provider.analizar_sentimiento.side_effect = Exception("Error de API")
        
        use_case = AnalizarSentimientoUseCase(mock_provider)
        
        # Act
        resultado = use_case.execute("Estoy muy contento con el servicio")
        
        # Assert
        assert isinstance(resultado, AnalisisSentimiento)
        assert resultado.sentimiento == "neutral"  # Valor por defecto
        assert resultado.confianza == 0.5  # Valor por defecto
        assert len(resultado.emociones) == 0  # Lista vacía
        mock_provider.analizar_sentimiento.assert_called_once()