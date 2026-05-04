import jwt
import pyotp
from .config import setting
from pwdlib import PasswordHash
from app.util import AuthenticationError
from datetime import timedelta, datetime, timezone


password_hasher = PasswordHash.recommended()


def generate_token(token_type: str, subject: str):

    config = setting.TOKEN_CONFIG.get(token_type)

    if not config:
        raise ValueError(f"Invalid token type: {token_type}")

    expire = config["expiry"]

    payload = {
        "token_type": token_type,
        "sub": str(subject),  # JWT sub must be a string
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(seconds=expire),
    }

    token = jwt.encode(payload, setting.SECRET_KEY, setting.ALGORITHM)
    return token


def decode_token(token):
    try:
        payload = jwt.decode(token, setting.SECRET_KEY, algorithms=[setting.ALGORITHM])

        sub = payload["sub"]
        # Try to convert to int (for user_id), otherwise keep as string (for email)
        try:
            user_id = int(sub)
        except ValueError:
            user_id = sub  # Keep as string for email

        if payload.get("token_type") != "refresh":
            raise AuthenticationError("Invalid token type")

        return user_id

    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Refresh token expired")

    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid refresh token")


def generate_OTP():
    otp = pyotp.TOTP(pyotp.random_base32(), digits=4, interval=120)
    return otp.now()
