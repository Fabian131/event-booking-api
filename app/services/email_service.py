import smtplib
<<<<<<< Updated upstream
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
=======
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings


class EmailService:
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_from = settings.SMTP_FROM_EMAIL
        self.smtp_use_tls = settings.SMTP_USE_TLS

    async def send_cancellation_email(
        self,
        to_email: str,
        user_name: str,
        event_title: str,
        event_date: str,
        ticket_quantity: int,
    ) -> None:
        subject = f"Reservation Cancelled - {event_title}"
        body = self._build_cancellation_body(user_name, event_title, event_date, ticket_quantity)
        await self._send_email(to_email, subject, body)

    async def _send_email(self, to_email: str, subject: str, html_body: str) -> None:
        if not self.smtp_host:
            return

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.smtp_from
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html"))

        await asyncio.to_thread(self._send_smtp, msg, to_email)

    def _send_smtp(self, msg: MIMEMultipart, to_email: str) -> None:
        if self.smtp_use_tls:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)

        if self.smtp_user and self.smtp_password:
            server.login(self.smtp_user, self.smtp_password)

        server.sendmail(self.smtp_from, to_email, msg.as_string())
        server.quit()

    def _build_cancellation_body(
        self,
        user_name: str,
        event_title: str,
        event_date: str,
        ticket_quantity: int,
    ) -> str:
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #e74c3c;">Reservation Cancelled</h2>
                <p>Hello {user_name},</p>
                <p>Your reservation has been successfully cancelled as requested.</p>
                <table style="border-collapse: collapse; width: 100%; margin: 20px 0;">
                    <tr>
                        <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Event</td>
                        <td style="padding: 10px; border: 1px solid #ddd;">{event_title}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Date</td>
                        <td style="padding: 10px; border: 1px solid #ddd;">{event_date}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Tickets Released</td>
                        <td style="padding: 10px; border: 1px solid #ddd;">{ticket_quantity}</td>
                    </tr>
                </table>
                <p>Your ticket slots have been returned to the public pool.</p>
                <p style="color: #999; font-size: 12px; margin-top: 30px;">
                    If you did not request this cancellation, please contact support immediately.
                </p>
>>>>>>> Stashed changes
            </div>
        </body>
        </html>
        """
<<<<<<< Updated upstream

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
=======
>>>>>>> Stashed changes
