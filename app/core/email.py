import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import setting
from app.core.middlewares.global_logger import get_logger

logger = get_logger("EMAIL_CORE")


def send_otp_email(email: str, username: str, otp: str) -> bool:
    subject = "Verify Email via OTP"

    body = f"""
            Hello {username},

            Thank you for registering! Please use the following OTP to verify your email:

            OTP: {otp}

            This OTP is valid for 5 minutes.

            If you didn't create an account, please ignore this email.

            Best regards,  
            Meton
        """

    sender_email = setting.SMTP_USER
    sender_password = setting.SMTP_PASSWORD

    message = MIMEMultipart()
    message["From"] = setting.SMTP_FROM or sender_email
    message["To"] = email
    message["Subject"] = subject

    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(setting.SMTP_HOST, setting.SMTP_PORT) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(message)
        return True
    except Exception as e:
        logger.error(f"Email error: {str(e)}")
        return False


def send_signup_otp_email(email: str, username: str, otp: str) -> bool:
    subject = "Verify Email via OTP"

    body = f"""
Hello {username},

Thank you for registering! Please use the following OTP to verify your email:

OTP: {otp}

This OTP is valid for 5 minutes.

If you didn't create an account, please ignore this email.

Best regards,  
Meton
"""

    return send_email(email, subject, body)


def send_forgot_password_email(email: str, username: str, otp: str) -> bool:
    subject = "Reset Your Password"

    body = f"""
Hello {username},

We received a request to reset your password.

Use the OTP below to proceed:

OTP: {otp}

This OTP is valid for 5 minutes.

If you didn't request this, please ignore this email.

Best regards,  
Meton
"""

    return send_email(email, subject, body)


def send_email(to_email: str, subject: str, body: str) -> bool:
    sender_email = setting.SMTP_USER
    sender_password = setting.SMTP_PASSWORD

    message = MIMEMultipart()
    message["From"] = setting.SMTP_FROM or sender_email
    message["To"] = to_email
    message["Subject"] = subject

    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(setting.SMTP_HOST, setting.SMTP_PORT) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(message)
        return True
    except Exception as e:
        logger.error(f"Email error: {str(e)}")
        return False