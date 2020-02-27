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

        if close:
            self.headers.update({"Connection":"close"})

        self.logger = logging.getLogger("nest")

    def request(self, method, *args, **kwargs):
        url = urljoin(self.prefix, "/".join(args))
        return super().request(method, url, **kwargs)

    def get_products_list(self):
        return self.get("products")

    def get_products(self, products):
        return self.get("products", ",".join(products))

    def get_events(self, _type, **kwargs):
        url = urljoin("events/", _type)
        res = self.get(url, params=kwargs)

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

        while data.get("nextPage"):
            page = data.get("nextPage")
            url = urljoin("events/", _type)
            res = self.get(url, params={**kwargs, "page":page})
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
            yield data.get("events")

    def get_orders(self, **kwargs):
        res = self.get("orders", params=kwargs)

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

        while data.get("nextPage"):
            page = data.get("nextPage")
            res = self.get("orders", params={**kwargs, "page":page})
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

    def get_parents(self, with_bundles=False):
        products = []
        res = self.get_products_list()

        try:
            res.raise_for_status()
            json_data = res.json()
            products.extend(json_data.get("products", []))
        except (HTTPError) as error:
            self.logger.error(f"Could not get products list: {error}")
            return {}
        except (JSONDecodeError) as error:
            self.logger.error(f"Could not decode response JSON: {error}")
            return {}

        if len(products) == 0:
            return {}

        res = self.get_products(products)

        data = []
        try:
            res.raise_for_status()
            json_data = res.json()
            data.extend(json_data.get("products", []))
        except (HTTPError) as error:
            self.logger.error(f"Could not get product data: {error}")
            return {}
        except (JSONDecodeError) as error:
            self.logger.error(f"Could not decode response JSON: {error}")
            return {}

        parent_information = defaultdict(list)
        for info in data:
            offers = info.get("offers", [])

            blacklist = []
            if not(with_bundles):
                blacklist.append("bundle")

            # Skip if blacklisted
            blacklisted = False
            for offer in offers:
                if offer.get("type") in blacklist:
                    blacklisted = True

            if blacklisted:
                continue

            # This must be the child of some product
            parent = info.get("parent")
            child = info.get("product")
            if parent and child:
                parent_information[parent].append(child)

        return parent_information

    def mark_event_processed(self, _id=""):
        url = urljoin("events/", _id)
        payload = {"processed":True}
        res = self.post(url, params=payload)
        try:
            res.raise_for_status()
        except (HTTPError) as error:
            self.logger.error(f"Could not mark event processed: {error}")
        return res
