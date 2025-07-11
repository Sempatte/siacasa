from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy import func, and_, case
from sqlalchemy.orm import Session

from .database import get_database_session, DBSession, DBMessage, DBDailyMetrics
from .models import SentimentType, ResolutionStatus, IntentType, DailyMetrics

class SIACASAMetricsAnalyzer:
    """Analizador de métricas específico para SIACASA"""
    
    def __init__(self):
        pass
    
    def _get_db(self):
        return next(get_database_session())
    
    def generate_daily_report(self, date: datetime) -> Dict[str, Any]:
        """Generar reporte diario específico para cajas rurales"""
        
        db = self._get_db()
        
        try:
            start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)
            
            # Consultar sesiones del día
            sessions = db.query(DBSession).filter(
                and_(
                    DBSession.start_time >= start_date,
                    DBSession.start_time < end_date
                )
            ).all()
            
            if not sessions:
                return {
                    "date": date.isoformat(),
                    "error": "No data found for SIACASA",
                    "total_sessions": 0
                }
            
            # Métricas básicas
            total_sessions = len(sessions)
            total_messages = sum(s.total_messages for s in sessions)
            
            # Métricas de efectividad bancaria
            successful_resolutions = sum(
                1 for s in sessions 
                if s.resolution_status == "exitosa"  # Cambiar de enum a string
            )
            escalated_sessions = sum(1 for s in sessions if s.escalation_required)
            
            # Mejora emocional (clave para SIACASA)
            emotional_improvements = sum(
                1 for s in sessions 
                if s.emotion_improvement
            )
            
            # Distribución de intents bancarios - CORREGIDO: Sin JOIN
            intent_counts = db.query(
                DBMessage.intent,
                func.count(DBMessage.id)
            ).filter(
                and_(
                    DBMessage.timestamp >= start_date,
                    DBMessage.timestamp < end_date,
                    DBMessage.intent.isnot(None)
                )
            ).group_by(DBMessage.intent).all()
            
            # Resto del método continúa igual...
            
            return {
                "date": date.isoformat(),
                "total_sessions": total_sessions,
                "total_messages": total_messages,
                "successful_resolutions": successful_resolutions,
                "escalated_sessions": escalated_sessions,
                "emotional_improvements": emotional_improvements,
                "intent_distribution": dict(intent_counts)
            }
            
        finally:
            db.close()
    
    def get_user_journey(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Obtener journey de un cliente específico"""
        
        db = self._get_db()
        
        try:
            since_date = datetime.utcnow() - timedelta(days=days)
            
            sessions = db.query(DBSession).filter(
                and_(
                    DBSession.user_id == user_id,
                    DBSession.start_time >= since_date
                )
            ).order_by(DBSession.start_time.desc()).all()
            
            if not sessions:
                return {
                    "user_id": user_id,
                    "message": "No se encontraron sesiones para este cliente",
                    "sessions": []
                }
            
            # Analizar evolución del cliente
            emotion_trend = []
            satisfaction_trend = []
            
            for session in reversed(sessions):  # Orden cronológico
                if session.final_sentiment:
                    emotion_trend.append({
                        "date": session.start_time.isoformat(),
                        "sentiment": session.final_sentiment,
                        "improvement": session.emotion_improvement
                    })
                
                if session.satisfaction_score:
                    satisfaction_trend.append({
                        "date": session.start_time.isoformat(),
                        "score": session.satisfaction_score
                    })
            
            # Calcular insights del cliente
            total_sessions = len(sessions)
            successful_sessions = sum(
                1 for s in sessions 
                if s.resolution_status == ResolutionStatus.EXITOSA.value
            )
            
            emotions_improved = sum(1 for s in sessions if s.emotion_improvement)
            avg_satisfaction = None
            if satisfaction_trend:
                avg_satisfaction = sum(t["score"] for t in satisfaction_trend) / len(satisfaction_trend)
            
            # Intent más común
            all_messages = []
            for session in sessions:
                messages = db.query(DBMessage).filter(
                    DBMessage.session_id == session.id
                ).all()
                all_messages.extend(messages)
            
            intent_counts = {}
            for msg in all_messages:
                intent_counts[msg.intent] = intent_counts.get(msg.intent, 0) + 1
            
            most_common_intent = max(intent_counts, key=intent_counts.get) if intent_counts else None
            
            return {
                "user_id": user_id,
                "total_sessions": total_sessions,
                "success_rate": round((successful_sessions / total_sessions * 100), 2) if total_sessions > 0 else 0,
                "avg_satisfaction": round(avg_satisfaction, 2) if avg_satisfaction else None,
                "most_common_intent": most_common_intent,
                "emotion_improvement_rate": round((emotions_improved / total_sessions * 100), 2) if total_sessions > 0 else 0,
                "last_interaction": sessions[0].start_time.isoformat() if sessions else None,
                "emotion_trend": emotion_trend,
                "satisfaction_trend": satisfaction_trend,
                "sessions_summary": [
                    {
                        "id": str(session.id),
                        "start_time": session.start_time.isoformat(),
                        "end_time": session.end_time.isoformat() if session.end_time else None,
                        "initial_sentiment": session.initial_sentiment,
                        "final_sentiment": session.final_sentiment,
                        "resolution_status": session.resolution_status,
                        "total_messages": session.total_messages,
                        "satisfaction_score": session.satisfaction_score,
                        "emotion_improvement": session.emotion_improvement,
                        "escalated": session.escalation_required
                    }
                    for session in sessions[:10]  # Solo últimas 10 sesiones
                ]
            }
        
        finally:
            db.close()
    
    def get_realtime_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas en tiempo real para el health check"""
        
        db = self._get_db()
        
        try:
            # Período de 24 horas
            since = datetime.utcnow() - timedelta(hours=24)
            
            # Sesiones activas en las últimas 24h
            active_sessions = db.query(func.count(DBSession.id)).filter(
                DBSession.start_time >= since
            ).scalar()
            
            # Total de mensajes en las últimas 24h
            total_messages_24h = db.query(func.count(DBMessage.id)).filter(
                DBMessage.timestamp >= since
            ).scalar()
            
            # Tiempo de respuesta promedio hoy
            avg_response_time_today = db.query(func.avg(DBMessage.processing_time_ms)).filter(
                DBMessage.timestamp >= since
            ).scalar() or 0
            
            # Sentimientos actuales
            current_sentiments = db.query(
                DBSession.final_sentiment,
                func.count(DBSession.id)
            ).filter(
                and_(
                    DBSession.start_time >= since,
                    DBSession.final_sentiment.isnot(None)
                )
            ).group_by(DBSession.final_sentiment).all()
            
            sentiment_dist = {
                sentiment: count 
                for sentiment, count in current_sentiments
            }
            
            # Top intents del día - CORREGIDO: Sin JOIN ambiguo
            top_intents = db.query(
                DBMessage.intent,
                func.count(DBMessage.id)
            ).filter(
                and_(
                    DBMessage.timestamp >= since,
                    DBMessage.intent.isnot(None)
                )
            ).group_by(DBMessage.intent).order_by(
                func.count(DBMessage.id).desc()
            ).limit(5).all()
            
            top_intents_dict = {intent: count for intent, count in top_intents}
            
            # Tasa de escalamiento del día
            escalated_today = db.query(func.count(DBSession.id)).filter(
                and_(
                    DBSession.start_time >= since,
                    DBSession.escalation_required == True
                )
            ).scalar()
            
            total_sessions_today = db.query(func.count(DBSession.id)).filter(
                DBSession.start_time >= since
            ).scalar()
            
            escalation_rate_today = (
                (escalated_today / total_sessions_today * 100) 
                if total_sessions_today > 0 else 0
            )
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "active_sessions_last_24h": active_sessions,
                "total_messages_today": total_messages_24h,
                "avg_response_time_today": round(avg_response_time_today, 2),
                "sentiment_distribution_today": sentiment_dist,
                "top_intents_today": top_intents_dict,
                "escalation_rate_today": round(escalation_rate_today, 2),
                "total_sessions_today": total_sessions_today
            }
        
        finally:
            db.close()
    
    def _save_daily_metrics(self, date: datetime, report: Dict[str, Any]):
        """Guardar métricas diarias en la base de datos"""
        
        db = self._get_db()
        
        try:
            start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Verificar si ya existe
            existing = db.query(DBDailyMetrics).filter(DBDailyMetrics.date == start_date).first()
            if existing:
                db.delete(existing)
            
            # Crear nueva entrada
            daily_metric = DBDailyMetrics(
                date=start_date,
                total_sessions=report["metricas_generales"]["total_sessions"],
                total_messages=report["metricas_generales"]["total_messages"],
                avg_messages_per_session=report["metricas_generales"]["avg_messages_per_session"],
                resolution_rate=report["metricas_efectividad"]["resolution_rate"],
                escalation_rate=report["metricas_efectividad"]["escalation_rate"],
                sentiment_improvement_rate=report["metricas_efectividad"]["emotion_improvement_rate"],
                avg_satisfaction_score=report["metricas_satisfaccion"]["avg_satisfaction_score"],
                avg_session_duration_seconds=report["metricas_generales"]["avg_session_duration_seconds"],
                avg_response_time_ms=report["metricas_generales"]["avg_response_time_ms"],
                intent_distribution=report["distribucion_consultas_bancarias"],
                sentiment_distribution=report["distribucion_sentimientos"]
            )
            
            db.add(daily_metric)
            db.commit()
            
        except Exception as e:
            logger.error(f"Error saving daily metrics: {e}")
            db.rollback()
        finally:
            db.close()

# Instancia global
metrics_analyzer = SIACASAMetricsAnalyzer()