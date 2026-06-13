import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


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
        subject = f"Reservacion Cancelada - {event_title}"
        body = self._build_cancellation_body(user_name, event_title, event_date, ticket_quantity)
        await self._send_email(to_email, subject, body)

    async def _send_email(self, to_email: str, subject: str, html_body: str) -> None:
        if not self.smtp_host:
            logger.warning("SMTP_HOST not configured. Skipping email send.")
            return

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.smtp_from
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html"))

        await asyncio.to_thread(self._send_smtp, msg, to_email)

    def _send_smtp(self, msg: MIMEMultipart, to_email: str) -> None:
        try:
            if self.smtp_use_tls:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)

            if self.smtp_user and self.smtp_password:
                server.login(self.smtp_user, self.smtp_password)

            server.sendmail(self.smtp_from, to_email, msg.as_string())
            server.quit()
            logger.info(f"Cancellation email sent successfully to {to_email}")
        except Exception as e:
            logger.error(f"Failed to send cancellation email to {to_email}: {e}")

    def _build_cancellation_body(
        self,
        user_name: str,
        event_title: str,
        event_date: str,
        ticket_quantity: int,
    ) -> str:
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Reservacion Cancelada</title>
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
                .details-table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 20px 0;
                }}
                .details-table td {{
                    padding: 10px;
                    border: 1px solid #ddd;
                }}
                .details-table td:first-child {{
                    font-weight: bold;
                    background-color: #f9f9f9;
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
                    <p>Tu reservacion ha sido cancelada exitosamente.</p>
                    <table class="details-table">
                        <tr>
                            <td>Evento</td>
                            <td>{event_title}</td>
                        </tr>
                        <tr>
                            <td>Fecha</td>
                            <td>{event_date}</td>
                        </tr>
                        <tr>
                            <td>Boletos liberados</td>
                            <td>{ticket_quantity}</td>
                        </tr>
                    </table>
                    <p>Tus boletos han sido devueltos al pool publico y estan disponibles para otros usuarios.</p>
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
