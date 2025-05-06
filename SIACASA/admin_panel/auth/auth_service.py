# admin_panel/auth/auth_service.py
import logging
import uuid
from datetime import datetime, timedelta
import jwt
from werkzeug.security import generate_password_hash, check_password_hash
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

logger = logging.getLogger(__name__)

class AuthService:
    """
    Servicio para manejar la autenticación de usuarios.
    """
    
    def __init__(self, db_connector):
        """
        Inicializa el servicio de autenticación.
        
        Args:
            db_connector: Conector a la base de datos
        """
        self.db = db_connector
        self.jwt_secret = os.getenv('JWT_SECRET_KEY', os.urandom(24).hex())
        self.reset_token_expiry = int(os.getenv('RESET_TOKEN_EXPIRY_MINUTES', 30))
        
        # Configuración de email
        self.smtp_server = os.getenv('SMTP_SERVER')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.smtp_user = os.getenv('SMTP_USER')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.email_sender = os.getenv('EMAIL_SENDER', 'no-reply@siacasa.com')
        self.admin_url = os.getenv('ADMIN_PANEL_URL', 'http://localhost:5000')
    
    def authenticate(self, username, password):
        """
        Autentica a un usuario mediante nombre de usuario y contraseña.
        
        Args:
            username: Nombre de usuario o correo electrónico
            password: Contraseña
            
        Returns:
            dict: Información del usuario si la autenticación es exitosa, None si falla
        """
        try:
            # Intentar obtener usuario por nombre de usuario o email
            query = """
                SELECT id, name, email, password_hash, role, bank_code, 
                    (SELECT name FROM banks WHERE code = admin_users.bank_code) as bank_name,
                    is_active
                FROM admin_users 
                WHERE (username = %s OR email = %s) AND is_active = TRUE
            """
            
            user = self.db.fetch_one(query, (username, username))
            
            if not user:
                logger.warning(f"Intento de inicio de sesión con usuario inexistente: {username}")
                return None
            
            # Verificar si la contraseña es correcta
            if check_password_hash(user['password_hash'], password):
                # Actualizar último inicio de sesión
                self.db.execute(
                    "UPDATE admin_users SET last_login = %s WHERE id = %s",
                    (datetime.now(), user['id'])
                )
                
                # Devolver información del usuario (excepto contraseña)
                del user['password_hash']
                return user
            
            logger.warning(f"Contraseña incorrecta para usuario: {username}")
            return None
        
        except Exception as e:
            logger.error(f"Error en autenticación: {e}", exc_info=True)
            raise
    
    def email_exists(self, email):
        """
        Verifica si existe un usuario con el correo electrónico especificado.
        
        Args:
            email: Correo electrónico a verificar
            
        Returns:
            bool: True si existe, False si no
        """
        try:
            query = "SELECT id FROM admin_users WHERE email = %s AND is_active = TRUE"
            result = self.db.fetch_one(query, (email,))
            return result is not None
        
        except Exception as e:
            logger.error(f"Error al verificar email: {e}", exc_info=True)
            raise
    
    def generate_reset_token(self, user_id):
        """
        Genera un token para restablecer contraseña.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            str: Token de restablecimiento
        """
        try:
            # Generar payload del token
            payload = {
                'user_id': user_id,
                'exp': datetime.utcnow() + timedelta(minutes=self.reset_token_expiry)
            }
            
            # Codificar token JWT
            token = jwt.encode(payload, self.jwt_secret, algorithm='HS256')
            
            # Guardar token en la base de datos
            self.db.execute(
                "UPDATE admin_users SET reset_token = %s, reset_token_expiry = %s WHERE id = %s",
                (token, payload['exp'], user_id)
            )
            
            return token
        
        except Exception as e:
            logger.error(f"Error al generar token: {e}", exc_info=True)
            raise
    
    def verify_reset_token(self, token):
        """
        Verifica si un token de restablecimiento es válido.
        
        Args:
            token: Token a verificar
            
        Returns:
            dict: Información del usuario si el token es válido, None si no
        """
        try:
            # Decodificar token
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            user_id = payload.get('user_id')
            
            # Verificar si el token es válido en la base de datos
            query = """
                SELECT id, name, email 
                FROM admin_users 
                WHERE id = %s AND reset_token = %s AND reset_token_expiry > %s
            """
            
            user = self.db.fetch_one(query, (user_id, token, datetime.utcnow()))
            return user
        
        except jwt.ExpiredSignatureError:
            logger.warning(f"Token expirado: {token}")
            return None
        
        except (jwt.InvalidTokenError, Exception) as e:
            logger.error(f"Error al verificar token: {e}", exc_info=True)
            return None
    
    def reset_password(self, user_id, new_password):
        """
        Restablece la contraseña de un usuario.
        
        Args:
            user_id: ID del usuario
            new_password: Nueva contraseña
        """
        try:
            # Generar hash de la nueva contraseña
            password_hash = generate_password_hash(new_password)
            
            # Actualizar contraseña y eliminar token
            self.db.execute(
                """
                UPDATE admin_users 
                SET password_hash = %s, reset_token = NULL, reset_token_expiry = NULL 
                WHERE id = %s
                """,
                (password_hash, user_id)
            )
            
            logger.info(f"Contraseña restablecida para usuario ID: {user_id}")
        
        except Exception as e:
            logger.error(f"Error al restablecer contraseña: {e}", exc_info=True)
            raise
    
    def send_reset_password_email(self, email):
        """
        Envía un correo con un enlace para restablecer la contraseña.
        
        Args:
            email: Correo electrónico del usuario
        """
        try:
            # Obtener información del usuario
            query = "SELECT id, name FROM admin_users WHERE email = %s"
            user = self.db.fetch_one(query, (email,))
            
            if not user:
                logger.warning(f"Intento de recuperación para email inexistente: {email}")
                return
            
            # Generar token
            token = self.generate_reset_token(user['id'])
            
            # Crear enlace de restablecimiento
            reset_link = f"{self.admin_url}/auth/reset-password/{token}"
            
            # Crear mensaje
            msg = MIMEMultipart()
            msg['Subject'] = 'Restablecimiento de Contraseña - SIACASA'
            msg['From'] = self.email_sender
            msg['To'] = email
            
            # Contenido HTML del correo
            html = f"""
            <html>
            <body style="font-family: Arial, sans-serif;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2>Restablecimiento de Contraseña</h2>
                    <p>Hola {user['name']},</p>
                    <p>Has solicitado restablecer tu contraseña para el Panel de Administración SIACASA.</p>
                    <p>Haz clic en el siguiente enlace para crear una nueva contraseña:</p>
                    <p>
                        <a href="{reset_link}" style="background-color: #004a87; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px;">
                            Restablecer Contraseña
                        </a>
                    </p>
                    <p>Este enlace expirará en {self.reset_token_expiry} minutos.</p>
                    <p>Si no solicitaste este cambio, puedes ignorar este correo y tu contraseña permanecerá sin cambios.</p>
                    <p>Saludos,<br>El equipo de SIACASA</p>
                </div>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html, 'html'))
            
            # Enviar correo
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Correo de recuperación enviado a: {email}")
        
        except Exception as e:
            logger.error(f"Error al enviar correo: {e}", exc_info=True)
            raise