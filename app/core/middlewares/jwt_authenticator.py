import jwt
from app.core.config import setting
from fastapi import Request
from app.util.response_util.custom_exception import (
    AuthenticationError,
    AccessTokenExpired,
)


def get_current_user_id(request: Request):
    token = request.cookies.get("access_token")

    if not token:
        raise AuthenticationError("Not logged in")

    try:
        payload = jwt.decode(token, setting.SECRET_KEY, algorithms=[setting.ALGORITHM])
        sub = payload["sub"]
        # Try to convert to int (for user_id), otherwise keep as string (for email)
        try:
            user_id = int(sub)
        except ValueError:
            user_id = sub  # Keep as string for email
        return user_id

    except jwt.ExpiredSignatureError as e:
        raise AccessTokenExpired("Access token expired")
    except jwt.InvalidTokenError as e:
        raise AuthenticationError("Invalid token")
    except Exception as e:
        print(f"[DEBUG] Unexpected JWT error: {type(e).__name__}: {e}")
        raise AuthenticationError("Invalid token")
