import logging
import aiosmtplib
from email.message import EmailMessage
from jinja2 import Environment, FileSystemLoader, select_autoescape
from app.core.config import settings

logger = logging.getLogger(__name__)

tenv = Environment(
    loader=FileSystemLoader("app/templates/emails"),
    autoescape=select_autoescape(['html', 'xml'])
)

async def send_password_reset_email(
    email: str,
    token: str
) -> None:
    message = EmailMessage()

    message['From'] = settings.smtp_from
    message['To'] = email
    message['Subject'] = 'Восстановление пароля'

    reset_link = (
        f"{settings.frontend_url}"
        f"/reset-password?token={token}"
    )

    logger.info(
        "Password reset email sent for %s",
        email,
    )

    text = tenv.get_template('password_reset.txt').render(
        reset_link=reset_link,
        expires_minutes=settings.password_reset_token_expire_minutes
    )

    html = tenv.get_template('password_reset.html').render(
        reset_link=reset_link,
        expires_minutes=settings.password_reset_token_expire_minutes
    )

    message.set_content(text)
    message.add_alternative(
        html,
        subtype='html'
    )


    await aiosmtplib.send(
        message,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_username,
        password=settings.smtp_password,
        start_tls=settings.smtp_use_tls
    )