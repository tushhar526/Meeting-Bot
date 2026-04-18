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

    expire = config["expire"]

    payload = {
        "token_type": token_type,
        "sub": subject,  # email OR user_id
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(seconds=expire),
    }

    token = jwt.encode(payload, setting.SECRET_KEY, setting.ALGORITHM)
    return token


def decode_token(token):
    try:
        payload = jwt.decode(token, setting.SECRET_KEY, algorithms=[setting.ALGORITHM])

        user_id = payload["sub"]

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
