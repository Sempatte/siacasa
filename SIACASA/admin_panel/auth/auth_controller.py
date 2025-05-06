# admin_panel/auth/auth_controller.py
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash

from admin_panel.auth.auth_service import AuthService
from bot_siacasa.infrastructure.db.neondb_connector import NeonDBConnector

logger = logging.getLogger(__name__)

# Crear blueprint para autenticación
auth_blueprint = Blueprint('auth', __name__)

# Inicializar servicio de autenticación
auth_service = AuthService(NeonDBConnector())

@auth_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    """
    Maneja el proceso de inicio de sesión.
    """
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        # Obtener datos del formulario
        username = request.form.get('username')
        password = request.form.get('password')
        remember = 'remember' in request.form
        
        if not username or not password:
            flash('Por favor, completa todos los campos.', 'danger')
            return render_template('login.html')
        
        try:
            # Intentar autenticar al usuario
            user = auth_service.authenticate(username, password)
            
            if user:
                # Establecer sesión
                session.permanent = remember
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                session['bank_code'] = user['bank_code']
                session['bank_name'] = user['bank_name']
                session['role'] = user['role']
                
                logger.info(f"Inicio de sesión exitoso para usuario: {username}")
                
                # Redireccionar al dashboard
                return redirect(url_for('dashboard'))
            else:
                flash('Credenciales incorrectas. Por favor, intenta de nuevo.', 'danger')
                logger.warning(f"Intento de inicio de sesión fallido para usuario: {username}")
                
        except Exception as e:
            flash('Error al iniciar sesión. Por favor, intenta de nuevo más tarde.', 'danger')
            logger.error(f"Error en inicio de sesión: {e}", exc_info=True)
    
    return render_template('login.html')

@auth_blueprint.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """
    Maneja el proceso de recuperación de contraseña.
    """
    if request.method == 'POST':
        email = request.form.get('email')
        
        if not email:
            flash('Por favor, ingresa tu correo electrónico.', 'danger')
            return render_template('forgot_password.html')
        
        try:
            # Verificar si el email existe
            if auth_service.email_exists(email):
                # Enviar correo de recuperación
                auth_service.send_reset_password_email(email)
                flash('Se ha enviado un correo con instrucciones para restablecer tu contraseña.', 'success')
                return redirect(url_for('auth.login'))
            else:
                flash('No existe una cuenta con ese correo electrónico.', 'danger')
        
        except Exception as e:
            flash('Error al procesar la solicitud. Por favor, intenta de nuevo más tarde.', 'danger')
            logger.error(f"Error en recuperación de contraseña: {e}", exc_info=True)
    
    return render_template('forgot_password.html')

@auth_blueprint.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """
    Maneja el proceso de restablecimiento de contraseña.
    """
    # Verificar token
    user = auth_service.verify_reset_token(token)
    
    if not user:
        flash('El enlace para restablecer la contraseña es inválido o ha expirado.', 'danger')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not password or not confirm_password:
            flash('Por favor, completa todos los campos.', 'danger')
            return render_template('reset_password.html')
        
        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('reset_password.html')
        
        try:
            # Cambiar contraseña
            auth_service.reset_password(user['id'], password)
            flash('Tu contraseña ha sido actualizada correctamente. Ahora puedes iniciar sesión.', 'success')
            return redirect(url_for('auth.login'))
        
        except Exception as e:
            flash('Error al restablecer la contraseña. Por favor, intenta de nuevo más tarde.', 'danger')
            logger.error(f"Error al restablecer contraseña: {e}", exc_info=True)
    
    return render_template('reset_password.html')