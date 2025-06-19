# admin_panel/analytics/analytics_controller.py
import logging
import requests
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify

from admin_panel.auth.auth_middleware import login_required
from bot_siacasa.infrastructure.db.neondb_connector import NeonDBConnector

logger = logging.getLogger(__name__)

# Crear blueprint para analytics
analytics_blueprint = Blueprint('analytics', __name__)

class AnalyticsService:
    """Servicio para obtener métricas del sistema"""
    
    def __init__(self):
        self.base_url = "http://localhost:3200/api/metrics"
        
    def get_health_status(self):
        """Obtener estado de salud del sistema"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                return response.json()
            return {"status": "unhealthy", "error": "API no disponible"}
        except Exception as e:
            logger.error(f"Error getting health status: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    def get_realtime_stats(self):
        """Obtener estadísticas en tiempo real"""
        try:
            response = requests.get(f"{self.base_url}/realtime-stats", timeout=5)
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            logger.error(f"Error getting realtime stats: {e}")
            return {}
    
    def get_daily_report(self, date=None):
        """Obtener reporte diario"""
        try:
            url = f"{self.base_url}/daily-report"
            if date:
                url += f"?date={date}"
            
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            logger.error(f"Error getting daily report: {e}")
            return {}
    
    def get_weekly_stats(self):
        """Obtener estadísticas de la semana"""
        weekly_data = []
        today = datetime.now().date()
        
        for i in range(7):
            date = today - timedelta(days=i)
            daily_report = self.get_daily_report(date.isoformat())
            if daily_report:
                weekly_data.append({
                    'date': date.isoformat(),
                    'sessions': daily_report.get('total_sessions', 0),
                    'messages': daily_report.get('total_messages', 0),
                    'escalations': daily_report.get('escalated_sessions', 0),
                    'satisfaction': daily_report.get('avg_satisfaction_score', 0)
                })
        
        return list(reversed(weekly_data))  # Ordenar de lunes a domingo

# Instancia del servicio
analytics_service = AnalyticsService()

@analytics_blueprint.route('/')
@login_required
def index():
    """Vista principal de analytics"""
    bank_code = session.get('bank_code')
    bank_name = session.get('bank_name')
    user_name = session.get('user_name')
    
    # Obtener datos
    health_status = analytics_service.get_health_status()
    realtime_stats = analytics_service.get_realtime_stats()
    daily_report = analytics_service.get_daily_report()
    weekly_stats = analytics_service.get_weekly_stats()
    
    # Preparar datos para gráficos
    chart_data = {
        'weekly_sessions': {
            'labels': [item['date'] for item in weekly_stats],
            'data': [item['sessions'] for item in weekly_stats]
        },
        'weekly_messages': {
            'labels': [item['date'] for item in weekly_stats],
            'data': [item['messages'] for item in weekly_stats]
        },
        'sentiment_distribution': realtime_stats.get('sentiment_distribution_today', {}),
        'intent_distribution': realtime_stats.get('top_intents_today', {})
    }
    
    return render_template(
        'analytics_dashboard.html',
        bank_name=bank_name,
        user_name=user_name,
        health_status=health_status,
        realtime_stats=realtime_stats,
        daily_report=daily_report,
        weekly_stats=weekly_stats,
        chart_data=chart_data
    )

@analytics_blueprint.route('/api/realtime-data')
@login_required
def api_realtime_data():
    """API para obtener datos en tiempo real (para actualización automática)"""
    try:
        health_status = analytics_service.get_health_status()
        realtime_stats = analytics_service.get_realtime_stats()
        
        return jsonify({
            'status': 'success',
            'health': health_status,
            'stats': realtime_stats,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error in realtime API: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@analytics_blueprint.route('/api/chart-data/<chart_type>')
@login_required
def api_chart_data(chart_type):
    """API para obtener datos específicos de gráficos"""
    try:
        if chart_type == 'weekly':
            data = analytics_service.get_weekly_stats()
        elif chart_type == 'daily':
            data = analytics_service.get_daily_report()
        elif chart_type == 'realtime':
            data = analytics_service.get_realtime_stats()
        else:
            return jsonify({'status': 'error', 'error': 'Tipo de gráfico no válido'}), 400
        
        return jsonify({
            'status': 'success',
            'data': data
        })
    except Exception as e:
        logger.error(f"Error getting chart data: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500