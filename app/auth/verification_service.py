from app.core.redis import redis_client
from app.util.response_util.custom_exception import InvalidVerificationToken
from app.core.middlewares.global_logger import get_logger

logger = get_logger("AUTH_VERIFY")


async def validate_verification_token(verification_token: str) -> str:
    if not verification_token:
        logger.warning("Verification token is empty or None")
        raise InvalidVerificationToken("Verification token is missing")

    redis_key = f"verify:{verification_token}"
    email = await redis_client.get(redis_key)

    if not email:
        logger.warning(
            f"Verification token not found or expired in Redis: {redis_key[:20]}..."
        )
        raise InvalidVerificationToken("Invalid or expired verification token")

    return email
