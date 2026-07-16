import logging

logger = logging.getLogger(__name__)

async def send_password_reset_email(
    email: str,
    token: str
):
    print('It works')
    logger.info(
        "Password reset link for %s: http://localhost:8000/reset-password?token=%s",
        email,
        token
    )