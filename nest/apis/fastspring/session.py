import logging
from collections import defaultdict
from json import JSONDecodeError
from os import environ
from urllib.parse import urljoin

from requests import HTTPError, Session


class FastSpring(Session):
    """docstring here
    """
    def __init__(self, auth=None, prefix=None, close=False, hooks={}, **kwargs):
        self.prefix = prefix or "https://api.fastspring.com"
        super().__init__(**kwargs)
        self.hooks = hooks
        self.auth = auth or (
            environ.get("FS_AUTH_USER", ""), 
            environ.get("FS_AUTH_PASS", "")
        )
        self.auth = (self.auth[0], self.auth[1])
        self.logger = logging.getLogger("nest")

    def request(self, method, url, *args, **kwargs):
        url = urljoin(self.prefix, "/".join([url]))
        return super().request(method, url, *args, **kwargs)

    def get_products(self, *args, **kwargs):
        plist = ",".join(args)

        res = self.request(
            "GET", 
            f"products/{plist}", 
            **kwargs
        )

        try:
            res.raise_for_status()
            data = res.json()
        except (HTTPError) as error:
            self.logger.error(f"Could not get orders: {error}")
            return []
        except (JSONDecodeError) as error:
            self.logger.error(f"Could not decode response JSON: {error}")
            return []
        
        for product in data.get("products", []):
            yield product

    def get_events(self, type, **kwargs):
        res = self.get(f"events/{type}", **kwargs)

        try:
            res.raise_for_status()
            data = res.json()
        except (HTTPError) as error:
            self.logger.error(f"Could not get orders: {error}")
            return []
        except (JSONDecodeError) as error:
            self.logger.error(f"Could not decode response JSON: {error}")
            return []

        yield data.get("events", [])

        # Drop any unnecessary params
        kwargs["params"] = kwargs.get("params", {})
        kwargs["params"].pop("days", None)

        while data.get("more"):
            # Change "begin" param to the last order timestamp
            events = data.get("events", [{}])
            timestamp = events[-1].get("created")
            if not(timestamp):
                break
            
            kwargs["params"].update(begin=timestamp+1)
            res = self.get(f"events/{type}", **kwargs)

            try:
                res.raise_for_status()
                data = res.json()
            except (HTTPError) as error:
                self.logger.error(
                    f"Could not get orders from timestamp {timestamp}: {error}"
                )
                yield []
            except (JSONDecodeError) as error:
                self.logger.error(
                    f"Could not decode JSON from response ({timestamp}) "
                    f"{error}"
                )
                yield []
            yield data.get("events")

    def get_orders(self, *args, **kwargs):
        res = self.get("orders", *args, **kwargs)

        try:
            res.raise_for_status()
            data = res.json()
        except (HTTPError) as error:
            self.logger.error(f"Could not get orders: {error}")
            return []
        except (JSONDecodeError) as error:
            self.logger.error(f"Could not decode response JSON: {error}")
            return []

        yield data.get("orders", [])
            
        kwargs["params"] = kwargs.get("params", {})

        while data.get("nextPage"):
            page = data.get("nextPage")
            kwargs["params"].update(page=page)
            res = self.get("orders", **kwargs)
            try:
                res.raise_for_status()
                data = res.json()
            except (HTTPError) as error:
                self.logger.error(f"Could not get orders on page {page}: {error}")
                yield []
            except (JSONDecodeError) as error:
                self.logger.error(f"Could not decode response JSON on page {page}: "
                             f"{error}")
                yield []
            yield data.get("orders")

    def get_parents(self, *args, blacklist=["bundle"], **kwargs):
        products = [name for name in self.get_products(*args, **kwargs)]

        if len(products) == 0:
            return {}

        parent_information = defaultdict(list)
        for info in self.get_products(*products):
            offers = info.get("offers", [])

            if any([offer.get("type") in blacklist for offer in offers]):
                continue

            parent = info.get("parent")
            child = info.get("product")
            if parent and child:
                parent_information[parent].append(child)

        return parent_information

    def update_event(self, id, **kwargs):
        res = self.post(f"events/{id}", **kwargs)
        try:
            res.raise_for_status()
        except (HTTPError) as error:
            self.logger.error(f"Could not update event: {error}")
        return res
