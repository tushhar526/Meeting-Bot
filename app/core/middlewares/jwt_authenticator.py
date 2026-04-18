import jwt
from app.core import setting
from fastapi import Request
from app.util import AuthenticationError, AccessTokenExpired


def get_current_user_id(request: Request):
    token = request.cookies.get("access_token")

    if not token:
        raise AuthenticationError("Not logged in")

    try:

        payload = jwt.decode(token, setting.SECRET_KEY, algorithms=[setting.ALGORITHM])
        return payload["user_id"]

    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid token")
    except jwt.ExpiredSignatureError:
        raise AccessTokenExpired("Access token expired")
