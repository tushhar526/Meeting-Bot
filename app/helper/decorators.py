import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)


def retry(times=3, delay=5, backoff=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, times + 1):
                try:
                    # Add attempt info to kwargs only if function supports it
                    import inspect
                    sig = inspect.signature(func)
                    if '_attempt' in sig.parameters and '_max_attempts' in sig.parameters:
                        kwargs['_attempt'] = attempt
                        kwargs['_max_attempts'] = times
                    
                    result = func(*args, **kwargs)

                    if result is False:
                        logger.warning(
                            f"Attempt {attempt}/{times}: {func.__name__} returned False"
                        )

                        if attempt == times:
                            return False

                        current_delay = delay * (backoff ** (attempt - 1))
                        logger.info(
                            f"Retrying {func.__name__} in {current_delay}s... "
                            f"(Attempt {attempt}/{times})"
                        )
                        time.sleep(current_delay)
                        continue

                    if attempt > 1:
                        logger.info(
                            f"{func.__name__} succeeded on attempt {attempt}/{times}"
                        )
                    return result

                except Exception as e:
                    last_exception = e
                    logger.error(
                        f"Attempt {attempt}/{times}: {func.__name__} failed with {type(e).__name__}: {e}"
                    )

                    if attempt == times:
                        logger.error(f"All {times} attempts failed for {func.__name__}")
                        return False

                    current_delay = delay * (backoff ** (attempt - 1))
                    logger.info(
                        f"Retrying {func.__name__} in {current_delay}s... "
                        f"(Attempt {attempt}/{times})"
                    )
                    time.sleep(current_delay)

            return False

        return wrapper

    return decorator
