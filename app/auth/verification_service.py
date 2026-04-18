from app.core import redis_client
from app.util import InvalidVerificationToken


async def validate_verification_token(verification_token: str) -> str:
    email_bytes = await redis_client.get(f"verify:{verification_token}")

    if not email_bytes:
        raise InvalidVerificationToken()

    return email_bytes.decode()
