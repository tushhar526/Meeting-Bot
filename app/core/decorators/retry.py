import time
import inspect
import logging
from functools import wraps
from app.util import RetryException, NoRetryException

logger = logging.getLogger("RETRY")


def retry(
    times: int = 3,
    delay: float = 2,
    backoff: float = 2,
    retry_on: tuple = (RetryException,),
    retry_on_false: bool = True,
):
    """
    Retry decorator with exponential backoff.

    Args:
        times: max attempts
        delay: initial delay in seconds
        backoff: multiplier for delay (exponential)
        retry_on: exceptions to retry on
        retry_on_false: retry if function returns False
    """

    def decorator(func):
        sig = inspect.signature(func)
        supports_attempt = (
            "_attempt" in sig.parameters and "_max_attempts" in sig.parameters
        )

        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, times + 1):
                try:
                    # Inject attempt info if supported
                    if supports_attempt:
                        kwargs["_attempt"] = attempt
                        kwargs["_max_attempts"] = times

                    result = func(*args, **kwargs)

                    # Handle "soft failure"
                    if retry_on_false and result is False:
                        logger.warning(
                            f"{func.__name__} returned False "
                            f"(attempt {attempt}/{times})"
                        )

                        if attempt == times:
                            raise Exception(
                                f"{func.__name__} returned False after {times} attempts"
                            )

                    else:
                        if attempt > 1:
                            logger.info(
                                f"{func.__name__} succeeded on attempt {attempt}"
                            )
                        return result

                except NoRetryException as e:
                    logger.error(
                        f"{func.__name__} failed with non-retryable error: {e}"
                    )
                    raise

                except retry_on as e:
                    last_exception = e
                    logger.error(
                        f"{func.__name__} failed on attempt {attempt}/{times}: {e}"
                    )

                    if attempt == times:
                        logger.error(f"{func.__name__} failed after {times} attempts")
                        raise

                # Delay before next retry
                current_delay = delay * (backoff ** (attempt - 1))
                logger.info(f"Retrying {func.__name__} in {current_delay:.2f}s...")
                time.sleep(current_delay)

            # fallback (should not reach here)
            raise last_exception or Exception("Retry failed unexpectedly")

        return wrapper

    return decorator
