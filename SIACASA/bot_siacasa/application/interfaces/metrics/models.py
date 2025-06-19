from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID, uuid4

class SentimentType(str, Enum):
    POSITIVO = "positivo"
    NEUTRAL = "neutral"  
    NEGATIVO = "negativo"

class IntentType(str, Enum):
    CONSULTA_SALDO = "consulta_saldo"
    TRANSFERENCIA = "transferencia"
    PRESTAMO = "prestamo"
    AHORRO = "ahorro"
    TARJETA_CREDITO = "tarjeta_credito"
    INFORMACION_GENERAL = "informacion_general"
    RECLAMO = "reclamo"
    OTRO = "otro"

class ResolutionStatus(str, Enum):
    EXITOSA = "exitosa"
    PARCIAL = "parcial"
    FALLIDA = "fallida"
    ESCALADA = "escalada"
    ABANDONADA = "abandonada"

class MessageMetric(BaseModel):
    """Métrica por mensaje individual"""
    id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    timestamp: datetime = Field(default_factory=datetime.now)
    user_message: str
    bot_response: str
    sentiment: SentimentType
    sentiment_confidence: float = Field(ge=0, le=1)
    intent: IntentType
    intent_confidence: float = Field(ge=0, le=1)
    processing_time_ms: float
    token_count: int
    is_escalation_request: bool = False
    user_satisfaction: Optional[int] = Field(None, ge=1, le=5)  # 1-5 escala

class SessionMetric(BaseModel):
    """Métrica por sesión completa"""
    id: UUID = Field(default_factory=uuid4)
    user_id: str
    cliente_tipo: Optional[str] = None  # "nuevo", "recurrente", "premium"
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    initial_sentiment: SentimentType
    final_sentiment: Optional[SentimentType] = None
    resolution_status: Optional[ResolutionStatus] = None
    total_messages: int = 0
    escalation_required: bool = False
    satisfaction_score: Optional[int] = Field(None, ge=1, le=10)
    
    # Métricas específicas de SIACASA
    sentiment_journey: List[SentimentType] = []
    emotion_improvement: bool = False
    queries_resolved: int = 0
    total_processing_time_ms: float = 0
    total_tokens_used: int = 0
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }

class DailyMetrics(BaseModel):
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
    intent_distribution: dict = {}
    sentiment_distribution: dict = {}