from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy import func, and_
from sqlalchemy.orm import Session
from collections import Counter

# Se asume que estas importaciones son correctas para tu estructura de proyecto.
# Ajusta las rutas si es necesario.
from bot_siacasa.infrastructure.db.metrics_models import (
    DBSession, 
    DBMessage, 
    SentimentType, 
    ResolutionStatus, 
    IntentType, 
    DailyMetrics
)
from bot_siacasa.infrastructure.db.database import get_db

class SIACASAMetricsAnalyzer:
    """Analizador de métricas específico para SIACASA"""
    
    def __init__(self):
        """Inicializa el analizador."""
        self.db_session_generator = get_db()
        self.db: Optional[Session] = None
    
    def _get_db(self) -> Session:
        """
        Obtiene y gestiona una sesión de base de datos activa.
        """
        if not self.db or not self.db.is_active:
            self.db = next(self.db_session_generator)
        return self.db
    
    async def generate_daily_report(self, date: datetime) -> Dict[str, Any]:
        """Generar reporte diario específico para cajas rurales"""
        
        db = self._get_db()
        
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        
        # Consultar sesiones del día
        sessions = db.query(DBSession).filter(
            DBSession.start_time >= start_date,
            DBSession.start_time < end_date
        ).all()
        
        if not sessions:
            return {
                "date": start_date.date().isoformat(),
                "message": "No se encontraron sesiones para esta fecha.",
                "total_sessions": 0
            }
        
        # Métricas básicas
        total_sessions = len(sessions)
        total_messages = sum(s.message_count for s in sessions if s.message_count)
        
        # Métricas de resolución
        resolution_counts = Counter(s.resolution_status for s in sessions if s.resolution_status)
        resolved_sessions = resolution_counts.get(ResolutionStatus.RESOLVED, 0)
        escalated_sessions = resolution_counts.get(ResolutionStatus.ESCALATED, 0)
        
        # Métricas de sentimiento
        sentiment_counts = Counter(s.final_sentiment for s in sessions if s.final_sentiment)
        positive_sentiments = sentiment_counts.get(SentimentType.POSITIVE, 0)
        negative_sentiments = sentiment_counts.get(SentimentType.NEGATIVE, 0)
        
        # Satisfacción y duración
        valid_satisfaction_scores = [s.satisfaction_score for s in sessions if s.satisfaction_score is not None]
        avg_satisfaction = sum(valid_satisfaction_scores) / len(valid_satisfaction_scores) if valid_satisfaction_scores else 0
        
        valid_durations = [(s.end_time - s.start_time).total_seconds() for s in sessions if s.end_time]
        avg_duration = sum(valid_durations) / len(valid_durations) if valid_durations else 0
        
        # Análisis de intenciones
        messages = db.query(DBMessage.intent, func.count(DBMessage.intent)).filter(
            DBMessage.timestamp >= start_date,
            DBMessage.timestamp < end_date,
            DBMessage.intent.isnot(None)
        ).group_by(DBMessage.intent).all()
        
        intent_analysis = {intent.name: count for intent, count in messages}

        # Métricas de efectividad bancaria (ejemplos)
        successful_transfers = intent_analysis.get(IntentType.TRANSFERENCIA_EXITOSA, 0)
        balance_inquiries = intent_analysis.get(IntentType.CONSULTA_SALDO, 0)
        
        # Construir el reporte final
        return {
            "date": start_date.date().isoformat(),
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "resolution_status": {
                "resolved": resolved_sessions,
                "escalated": escalated_sessions,
                "unresolved": total_sessions - (resolved_sessions + escalated_sessions)
            },
            "satisfaction": {
                "average_score": round(avg_satisfaction, 2),
                "total_responses": len(valid_satisfaction_scores)
            },
            "performance": {
                "average_session_duration_seconds": round(avg_duration, 2)
            },
            "sentiment_analysis": {
                "positive": positive_sentiments,
                "negative": negative_sentiments,
                "neutral": sentiment_counts.get(SentimentType.NEUTRAL, 0)
            },
            "intent_analysis": intent_analysis,
            "bank_specific_metrics": {
                "successful_transfers": successful_transfers,
                "balance_inquiries": balance_inquiries
            }
        }
    
    async def get_user_journey(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Obtiene el viaje del cliente para un usuario específico."""
        db = self._get_db()
        start_date = datetime.now() - timedelta(days=days)

        sessions = db.query(DBSession).filter(
            DBSession.user_id == user_id,
            DBSession.start_time >= start_date
        ).order_by(DBSession.start_time.asc()).all()

        if not sessions:
            return {"user_id": user_id, "message": "No se encontraron sesiones para este usuario en el período dado."}

        total_sessions = len(sessions)
        successful_sessions = sum(1 for s in sessions if s.resolution_status == ResolutionStatus.RESOLVED)
        
        satisfaction_scores = [s.satisfaction_score for s in sessions if s.satisfaction_score is not None]
        avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else None

        session_details = [{
            "session_id": s.id,
            "start_time": s.start_time.isoformat(),
            "duration_seconds": (s.end_time - s.start_time).total_seconds() if s.end_time else None,
            "resolution": s.resolution_status.value if s.resolution_status else "N/A",
            "satisfaction": s.satisfaction_score,
            "escalated": s.escalation_required
        } for s in sessions]

        return {
            "user_id": user_id,
            "period_days": days,
            "total_sessions": total_sessions,
            "summary": {
                "successful_session_rate": round((successful_sessions / total_sessions * 100), 2) if total_sessions > 0 else 0,
                "avg_satisfaction_score": round(avg_satisfaction, 2) if avg_satisfaction is not None else None,
            },
            "sessions": session_details
        }

    def close_db(self):
        """Cierra la conexión a la base de datos si está abierta."""
        if self.db:
            self.db.close()
            self.db = None
