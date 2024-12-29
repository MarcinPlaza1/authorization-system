from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr
import os
from dotenv import load_dotenv
from jinja2 import Environment, select_autoescape, PackageLoader

load_dotenv()

# Konfiguracja email
email_config = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM", "noreply@example.com"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True
)

# Inicjalizacja Jinja2 dla szablonów email
env = Environment(
    loader=PackageLoader('app', 'templates/email'),
    autoescape=select_autoescape(['html', 'xml'])
)

class EmailService:
    def __init__(self):
        self.fastmail = FastMail(email_config)
        self.base_url = os.getenv("BASE_URL", "http://localhost:8000")

    async def send_password_reset_email(self, email: EmailStr, token: str):
        """Wysyła email z linkiem do resetowania hasła."""
        template = env.get_template('password_reset.html')
        reset_url = f"{self.base_url}/reset-password?token={token}"
        
        html = template.render(
            reset_url=reset_url,
            expires_in_minutes=30
        )
        
        message = MessageSchema(
            subject="Reset hasła",
            recipients=[email],
            body=html,
            subtype="html"
        )
        
        await self.fastmail.send_message(message)

    async def send_password_change_notification(self, email: EmailStr):
        """Wysyła powiadomienie o zmianie hasła."""
        template = env.get_template('password_changed.html')
        html = template.render()
        
        message = MessageSchema(
            subject="Hasło zostało zmienione",
            recipients=[email],
            body=html,
            subtype="html"
        )
        
        await self.fastmail.send_message(message)

email_service = EmailService() 