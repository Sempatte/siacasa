from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum

# Enumeraciones
class SentimentType(str, Enum):
    POSITIVO = "positivo"
    NEUTRAL = "neutral"
    NEGATIVO = "negativo"

class IntentTypeSIACASA(str, Enum):
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
    OTRO = "otro"

class ResolutionStatus(str, Enum):
    EXITOSA = "exitosa"
    PARCIAL = "parcial"
    FALLIDA = "fallida"
    ESCALADA = "escalada"
    ABANDONADA = "abandonada"

class ClienteType(str, Enum):
    AGRICULTOR = "agricultor"
    GANADERO = "ganadero"
    COMERCIANTE_RURAL = "comerciante_rural"
    EMPLEADO = "empleado"
    MICROEMPRESARIO = "microempresario"
    NUEVO = "nuevo"
    RECURRENTE = "recurrente"

# Esquemas de Request
class MessageMetricCreate(BaseModel):
    session_id: UUID
    user_message: str = Field(..., min_length=1, max_length=2000)
    bot_response: str = Field(..., min_length=1, max_length=2000)
    sentiment: SentimentType
    sentiment_confidence: float = Field(..., ge=0, le=1)
    intent: IntentTypeSIACASA
    intent_confidence: float = Field(..., ge=0, le=1)
    processing_time_ms: float = Field(..., gt=0)
    token_count: int = Field(..., gt=0)
    is_escalation_request: bool = False
    user_satisfaction: Optional[int] = Field(None, ge=1, le=5)
    detected_entities: Optional[Dict[str, Any]] = None
    response_tone: Optional[str] = None

class SessionMetricCreate(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=255)
    cliente_type: ClienteType = ClienteType.NUEVO
    initial_sentiment: SentimentType = SentimentType.NEUTRAL

class SessionMetricUpdate(BaseModel):
    end_time: Optional[datetime] = None
    final_sentiment: Optional[SentimentType] = None
    resolution_status: Optional[ResolutionStatus] = None
    escalation_required: Optional[bool] = None
    satisfaction_score: Optional[int] = Field(None, ge=1, le=10)
    sentiment_journey: Optional[List[str]] = None
    emotion_improvement: Optional[bool] = None
    banking_services_used: Optional[List[str]] = None

# Esquemas de Response
class MessageMetricResponse(BaseModel):
    id: UUID
    session_id: UUID
    timestamp: datetime
    user_message: str
    bot_response: str
    sentiment: str
    sentiment_confidence: float
    intent: str
    intent_confidence: float
    processing_time_ms: float
    token_count: int
    is_escalation_request: bool
    user_satisfaction: Optional[int]
    detected_entities: Optional[Dict[str, Any]]
    response_tone: Optional[str]

    class Config:
        from_attributes = True

class SessionMetricResponse(BaseModel):
    id: UUID
    user_id: str
    cliente_type: str
    start_time: datetime
    end_time: Optional[datetime]
    initial_sentiment: str
    final_sentiment: Optional[str]
    resolution_status: Optional[str]
    total_messages: int
    escalation_required: bool
    satisfaction_score: Optional[int]
    sentiment_journey: Optional[List[str]]
    emotion_improvement: bool
    queries_resolved: int
    banking_services_used: Optional[List[str]]
    total_processing_time_ms: float
    total_tokens_used: int
    duration_seconds: Optional[float]

    class Config:
        from_attributes = True

class DailyMetricsResponse(BaseModel):
    date: datetime
    total_sessions: int
    total_messages: int
    avg_messages_per_session: float
    resolution_rate: float
    escalation_rate: float
    sentiment_improvement_rate: float
    avg_satisfaction_score: Optional[float]
    avg_session_duration_seconds: float
    avg_response_time_ms: float
    intent_distribution: Optional[Dict[str, int]]
    sentiment_distribution: Optional[Dict[str, int]]

    class Config:
        from_attributes = True

# Esquemas para Analytics
class UserJourneyResponse(BaseModel):
    user_id: str
    total_sessions: int
    avg_satisfaction: Optional[float]
    most_common_intent: Optional[str]
    emotion_improvement_rate: float
    last_interaction: Optional[datetime]
    sessions: List[SessionMetricResponse]

class RealtimeStatsResponse(BaseModel):
    timestamp: datetime
    active_sessions_last_hour: int
    total_messages_today: int
    avg_response_time_today: float
    sentiment_distribution_today: Dict[str, int]
    top_intents_today: Dict[str, int]
    escalation_rate_today: float

# Validadores personalizados
class MessageMetricCreate(MessageMetricCreate):
    @validator('sentiment_confidence')
    def validate_sentiment_confidence(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('sentiment_confidence debe estar entre 0 y 1')
        return v

    @validator('intent_confidence')
    def validate_intent_confidence(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('intent_confidence debe estar entre 0 y 1')
        return v

    @validator('processing_time_ms')
    def validate_processing_time(cls, v):
        if v <= 0:
            raise ValueError('processing_time_ms debe ser mayor que 0')
        return v

class SessionMetricUpdate(SessionMetricUpdate):
    @validator('satisfaction_score')
    def validate_satisfaction_score(cls, v):
        if v is not None and not 1 <= v <= 10:
            raise ValueError('satisfaction_score debe estar entre 1 y 10')
        return v

    @validator('sentiment_journey')
    def validate_sentiment_journey(cls, v):
        if v is not None:
            valid_sentiments = [s.value for s in SentimentType]
            for sentiment in v:
                if sentiment not in valid_sentiments:
                    raise ValueError(f'Sentimiento inválido: {sentiment}')
        return v