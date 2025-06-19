from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import logging

from bot_siacasa.metrics.analyzer import metrics_analyzer
from bot_siacasa.metrics.collector import metrics_collector

logger = logging.getLogger(__name__)

# Crear blueprint para métricas
metrics_bp = Blueprint('metrics', __name__, url_prefix='/api/metrics')

@metrics_bp.route('/daily-report')
def get_daily_report():
    """Obtener reporte diario"""
    try:
        date_str = request.args.get('date')
        if not date_str:
            date_obj = datetime.now().date()
        else:
            date_obj = datetime.fromisoformat(date_str).date()
        
        report = metrics_analyzer.generate_daily_report(datetime.combine(date_obj, datetime.min.time()))
        return jsonify(report)
        
    except ValueError:
        return jsonify({"error": "Formato de fecha inválido"}), 400
    except Exception as e:
        logger.error(f"Error getting daily report: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

@metrics_bp.route('/realtime-stats')
def get_realtime_stats():
    """Obtener estadísticas en tiempo real"""
    try:
        stats = metrics_analyzer.get_realtime_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting realtime stats: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

@metrics_bp.route('/user/<user_id>/journey')
def get_user_journey(user_id):
    """Obtener journey de un usuario"""
    try:
        days = request.args.get('days', 30, type=int)
        journey = metrics_analyzer.get_user_journey(user_id, days)
        return jsonify(journey)
    except Exception as e:
        logger.error(f"Error getting user journey: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

@metrics_bp.route('/session/<session_id>/end', methods=['POST'])
def end_session(session_id):
    """Finalizar una sesión"""
    try:
        data = request.get_json()
        resolution_status = data.get('resolution_status', 'exitosa')
        satisfaction_score = data.get('satisfaction_score')
        escalation_required = data.get('escalation_required', False)
        
        metrics_collector.end_session_sync(
            session_id=session_id,
            resolution_status=resolution_status,
            satisfaction_score=satisfaction_score,
            escalation_required=escalation_required
        )
        
        return jsonify({"status": "success", "message": "Sesión finalizada"})
        
    except Exception as e:
        logger.error(f"Error ending session: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

@metrics_bp.route('/health')
def health_check():
    """Verificar estado del sistema de métricas"""
    try:
        # Verificar conexión a BD
        stats = metrics_analyzer.get_realtime_stats()
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "connected",
            "active_sessions": stats.get("active_sessions_last_24h", 0)
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }), 500

def register_metrics_routes(app):
    """Registrar rutas de métricas en la aplicación Flask"""
    app.register_blueprint(metrics_bp)