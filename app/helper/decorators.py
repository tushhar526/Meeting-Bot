import time
import logging
from functools import wraps

"""decorator for retrying atleast n times before returning False as a product"""


logger = logging.getLogger(__name__)


def retry(times=3, delay=5):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempts in range(1, times + 1):
                try:
                    return func(*args, *kwargs)
                except Exception as e:
                    logger.error(f" Attempt = {attempts} and failed as for {e}")
                    time.sleep(delay)

            return False

        return wrapper

    return decorator
