import logging
from functools import wraps
from json import JSONDecodeError

from requests import HTTPError


def protect(default=None):
    """This decorator can be used on any method the requests some
    resource and expects:

    A) The response status to be non 4XX and non 5XX (aka, response OK)
    B) The response content to be parsable JSON

    In the event the method throws these errors uncaught, it will
    catch these errors (HTTPError and JSONDecodeError) and return
    the ``default`` value.

        :param default=None: Default value to return if exceptions are
        raised.
    """
    def wrapper(fn, *args, **kwargs):
        @wraps(fn)
        def wrapped(self, *args, **kwargs):
            logger = logging.getLogger("nest")

            rv = None
            try:
                rv = fn(self, *args, **kwargs)
            except (HTTPError) as error:
                url = error.response.url
                logger.error(f"Could not get {url}: {error}")
            except (JSONDecodeError) as error:
                logger.error(f"Could not decode response JSON: {error}")
            return rv or default
        return wrapped
    return wrapper
