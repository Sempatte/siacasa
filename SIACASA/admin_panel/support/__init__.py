"""
Módulo de soporte para el panel de administración de SIACASA.

Este módulo proporciona la funcionalidad para la escalación a humanos,
permitiendo que los agentes atiendan tickets de soporte generados cuando
los usuarios solicitan hablar con un humano o cuando el chatbot no puede 
resolver una consulta después de varios intentos.
"""

from admin_panel.support.support_controller import support_blueprint

__all__ = ['support_blueprint']