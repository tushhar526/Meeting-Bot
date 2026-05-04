from fastapi import Response
from app.core.config import setting
from datetime import timedelta


def set_auth_cookie(response: Response, token: str, token_type: str):
    config = setting.TOKEN_CONFIG.get(token_type)

    if not config:
        raise ValueError("Invalid token type")

    response.set_cookie(
        key=config["cookie_name"],
        value=token,
        httponly=setting.COOKIE_HTTPONLY,
        secure=setting.COOKIE_SECURE,
        samesite=setting.COOKIE_SAMESITE,
        max_age=int(config["expiry"]),
        path="/",
    )


def clear_auth_cookie(response: Response, token_type: str):
    """Clear an authentication cookie by setting it to expire immediately.
    
    Must use same path/secure settings as when the cookie was set.
    """
    config = setting.TOKEN_CONFIG.get(token_type)

    if not config:
        raise ValueError("Invalid token type")

    response.delete_cookie(
        key=config["cookie_name"],
        path="/",
        secure=setting.COOKIE_SECURE,
        httponly=setting.COOKIE_HTTPONLY,
        samesite=setting.COOKIE_SAMESITE,
    )
