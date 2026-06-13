import smtplib
from email.message import EmailMessage
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.user = settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL

    def send_reservation_cancelled_email(self, to_email: str, user_name: str, event_title: str):
        if not self.host or not self.user or not self.password:
            logger.warning("SMTP configuration is missing. Cannot send email.")
            return

        subject = f"Reservación Cancelada - {event_title}"
        
        # HTML Template using the blue (#0082A8) and white colors
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Reservación Cancelada</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f4f4f4;
                    margin: 0;
                    padding: 0;
                }}
                .container {{
                    max-width: 600px;
                    margin: 20px auto;
                    background-color: #ffffff;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                }}
                .header {{
                    background-color: #0082A8;
                    color: #ffffff;
                    padding: 20px;
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 24px;
                }}
                .content {{
                    padding: 30px 20px;
                    color: #333333;
                    line-height: 1.6;
                }}
                .content h2 {{
                    color: #0082A8;
                }}
                .footer {{
                    background-color: #f4f4f4;
                    color: #777777;
                    text-align: center;
                    padding: 15px;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Event Booking</h1>
                </div>
                <div class="content">
                    <h2>Hola, {user_name}</h2>
                    <p>Te escribimos para informarte que tu reservación para el evento <strong>{event_title}</strong> ha sido cancelada por un administrador.</p>
                    <p>Si tienes alguna duda o consideras que esto es un error, por favor ponte en contacto con nosotros.</p>
                    <p>Esperamos verte pronto en futuros eventos.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2026 Event Booking. Todos los derechos reservados.</p>
                </div>
            </div>
        </body>
        </html>
        """

        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = self.from_email
        msg['To'] = to_email
        msg.set_content(f"Hola {user_name}, tu reservación para el evento {event_title} ha sido cancelada.")
        msg.add_alternative(html_content, subtype='html')

        try:
            with smtplib.SMTP(self.host, self.port) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.send_message(msg)
                logger.info(f"Cancellation email sent successfully to {to_email}")
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")

email_service = EmailService()
