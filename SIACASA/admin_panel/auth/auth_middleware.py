# admin_panel/auth/auth_middleware.py
from functools import wraps
from flask import session, redirect, url_for, flash, request
import logging

logger = logging.getLogger(__name__)

def login_required(f):
    """
    Middleware para verificar si el usuario ha iniciado sesión.
    Redirige a la página de login si no hay sesión activa.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página.', 'warning')
            # Guardar la URL solicitada para redireccionar después del login
            session['next_url'] = request.url
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """
    Middleware para verificar si el usuario tiene rol de administrador.
    Redirige al dashboard si no tiene permisos suficientes.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página.', 'warning')
            return redirect(url_for('auth.login'))
        
        # Verificar rol de administrador
        if session.get('role') != 'admin':
            flash('No tienes permisos para acceder a esta sección.', 'danger')
            logger.warning(f"Usuario {session.get('user_id')} intentó acceder a sección de administrador sin permisos")
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

def bank_required(bank_codes):
    """
    Middleware para verificar si el usuario pertenece a los bancos especificados.
    Redirige al dashboard si no tiene permisos suficientes.
    
    Args:
        bank_codes: Lista de códigos de banco permitidos
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Debes iniciar sesión para acceder a esta página.', 'warning')
                return redirect(url_for('auth.login'))
            
            # Verificar código de banco
            user_bank = session.get('bank_code')
            if not user_bank or user_bank not in bank_codes:
                flash('No tienes permisos para acceder a esta sección.', 'danger')
                logger.warning(f"Usuario {session.get('user_id')} del banco {user_bank} intentó acceder a sección restringida")
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator