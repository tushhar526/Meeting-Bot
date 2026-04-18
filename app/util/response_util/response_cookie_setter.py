from fastapi import Response
from app.core import setting
from datetime import timedelta


def set_auth_cookie(response: Response, token: str, token_type: str):
    config = setting.TOKEN_CONFIG.get(token_type)

    if not config:
        raise ValueError("Invalid token type")

    response.set_cookie(
        key=config["cookie_name"],
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=int(config["expiry"]),
        path="/",
    )
