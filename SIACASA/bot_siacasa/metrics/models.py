from enum import Enum
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass
from uuid import UUID, uuid4

class SentimentType(str, Enum):
    POSITIVO = "positivo"
    NEUTRAL = "neutral"
    NEGATIVO = "negativo"

class IntentType(str, Enum):
    """Intents específicos para cajas rurales peruanas"""
    CONSULTA_SALDO = "consulta_saldo"
    TRANSFERENCIA = "transferencia"
    PRESTAMO_PERSONAL = "prestamo_personal"
    PRESTAMO_AGRICOLA = "prestamo_agricola"
    AHORRO_PROGRAMADO = "ahorro_programado"
    SEGURO_AGRICOLA = "seguro_agricola"
    TARJETA_DEBITO = "tarjeta_debito"
    INFORMACION_SUCURSAL = "informacion_sucursal"
    RECLAMO = "reclamo"
    CONSULTA_REQUISITOS = "consulta_requisitos"
    SALUDO = "saludo"
    DESPEDIDA = "despedida"
    OTRO = "otro"

class ResolutionStatus(str, Enum):
    EXITOSA = "exitosa"
    PARCIAL = "parcial"
    FALLIDA = "fallida"
    ESCALADA = "escalada"
    ABANDONADA = "abandonada"

class ClienteType(str, Enum):
    """Tipos de cliente específicos para cajas rurales"""
    AGRICULTOR = "agricultor"
    GANADERO = "ganadero"
    COMERCIANTE_RURAL = "comerciante_rural"
    EMPLEADO = "empleado"
    MICROEMPRESARIO = "microempresario"
    NUEVO = "nuevo"
    RECURRENTE = "recurrente"

@dataclass
class MessageMetric:
    """Entidad de dominio para métricas de mensaje"""
    id: UUID
    session_id: UUID
    timestamp: datetime
    user_message: str
    bot_response: str
    sentiment: SentimentType
    sentiment_confidence: float
    intent: IntentType
    intent_confidence: float
    processing_time_ms: float
    token_count: int
    is_escalation_request: bool
    user_satisfaction: Optional[int] = None
    detected_entities: Optional[Dict] = None
    response_tone: Optional[str] = None
    
    @classmethod
    def create(
        cls,
        session_id: UUID,
        user_message: str,
        bot_response: str,
        sentiment: SentimentType,
        sentiment_confidence: float,
        intent: IntentType,
        intent_confidence: float,
        processing_time_ms: float,
        token_count: int,
        is_escalation_request: bool = False,
        user_satisfaction: Optional[int] = None,
        detected_entities: Optional[Dict] = None,
        response_tone: Optional[str] = None
    ) -> 'MessageMetric':
        return cls(
            id=uuid4(),
            session_id=session_id,
            timestamp=datetime.utcnow(),
            user_message=user_message,
            bot_response=bot_response,
            sentiment=sentiment,
            sentiment_confidence=sentiment_confidence,
            intent=intent,
            intent_confidence=intent_confidence,
            processing_time_ms=processing_time_ms,
            token_count=token_count,
            is_escalation_request=is_escalation_request,
            user_satisfaction=user_satisfaction,
            detected_entities=detected_entities,
            response_tone=response_tone
        )
    
    def is_high_confidence(self) -> bool:
        """Determina si la predicción tiene alta confianza"""
        return (self.sentiment_confidence >= 0.8 and 
                self.intent_confidence >= 0.8)
    
    def is_negative_experience(self) -> bool:
        """Identifica experiencias negativas del usuario"""
        return (self.sentiment == SentimentType.NEGATIVO or
                self.is_escalation_request or
                (self.user_satisfaction is not None and self.user_satisfaction <= 2))

@dataclass
class SessionMetric:
    """Entidad de dominio para métricas de sesión"""
    id: UUID
    user_id: str
    cliente_type: ClienteType
    start_time: datetime
    end_time: Optional[datetime]
    initial_sentiment: SentimentType
    final_sentiment: Optional[SentimentType]
    resolution_status: Optional[ResolutionStatus]
    total_messages: int
    escalation_required: bool
    satisfaction_score: Optional[int]
    
    # Métricas específicas SIACASA
    sentiment_journey: List[SentimentType]
    emotion_improvement: bool
    queries_resolved: int
    banking_services_used: List[str]
    total_processing_time_ms: float
    total_tokens_used: int
    
    @classmethod
    def create(
        cls,
        user_id: str,
        cliente_type: ClienteType,
        initial_sentiment: SentimentType = SentimentType.NEUTRAL
    ) -> 'SessionMetric':
        return cls(
            id=uuid4(),
            user_id=user_id,
            cliente_type=cliente_type,
            start_time=datetime.utcnow(),
            end_time=None,
            initial_sentiment=initial_sentiment,
            final_sentiment=None,
            resolution_status=None,
            total_messages=0,
            escalation_required=False,
            satisfaction_score=None,
            sentiment_journey=[initial_sentiment],
            emotion_improvement=False,
            queries_resolved=0,
            banking_services_used=[],
            total_processing_time_ms=0,
            total_tokens_used=0
        )
    
    def duration_seconds(self) -> Optional[float]:
        """Calcula la duración de la sesión en segundos"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    def is_successful_session(self) -> bool:
        """Determina si la sesión fue exitosa"""
        return (self.resolution_status == ResolutionStatus.EXITOSA and
                not self.escalation_required and
                (self.satisfaction_score is None or self.satisfaction_score >= 4))
    
    def calculate_emotion_improvement(self) -> bool:
        """Calcula si hubo mejora emocional durante la sesión"""
        if len(self.sentiment_journey) < 2:
            return False
        
        initial = self.sentiment_journey[0]
        final = self.sentiment_journey[-1]
        
        # Mejora: Negativo -> Neutral/Positivo o Neutral -> Positivo
        if initial == SentimentType.NEGATIVO:
            return final in [SentimentType.NEUTRAL, SentimentType.POSITIVO]
        elif initial == SentimentType.NEUTRAL:
            return final == SentimentType.POSITIVO
        
        return False

@dataclass
class DailyMetrics:
    """Métricas agregadas diarias para SIACASA"""
    date: datetime
    total_sessions: int = 0
    total_messages: int = 0
    avg_messages_per_session: float = 0
    
    # Métricas de efectividad
    resolution_rate: float = 0  # % de consultas resueltas exitosamente
    escalation_rate: float = 0  # % de escalamientos a humanos
    sentiment_improvement_rate: float = 0  # % de mejora emocional
    
    # Métricas de satisfacción
    avg_satisfaction_score: Optional[float] = None
    nps_score: Optional[float] = None  # Net Promoter Score
    
    # Métricas operativas
    avg_session_duration_seconds: float = 0
    avg_response_time_ms: float = 0
    system_availability: float = 100.0
    
    # Distribución de consultas bancarias
    intent_distribution: Dict[str, int] = None
    sentiment_distribution: Dict[str, int] = None
    
    def __post_init__(self):
        if self.intent_distribution is None:
            self.intent_distribution = {}
        if self.sentiment_distribution is None:
            self.sentiment_distribution = {}