from os import environ
from urllib.parse import urljoin
from collections import defaultdict
from json import JSONDecodeError

from requests import Session, HTTPError

from . import logger

class FastSpring(Session):
    """Custom session with FastSpring's API prefixed"""
    def __init__(self, prefix=None, close=False, hooks={}, **kwargs):
        self.prefix = prefix or "https://api.fastspring.com"

        super().__init__(**kwargs)

        self.hooks = hooks
        self.auth = (environ.get("FS_AUTH_USER", b""),
                    environ.get("FS_AUTH_PASS", b""))

        if close:
            self.headers.update({'Connection':'close'})

    def request(self, method, url, *args, **kwargs):
        _url = urljoin(self.prefix, url)
        return super().request(method, _url, *args, **kwargs)

    def get_products_list(self):
        return self.get("products")

    def get_products(self, products):
        """Get information for one or more prodcuts

        Arguments:
            products {list} -- Product ID's
        """
        joined_ids = ",".join(products)
        url = urljoin("products/", joined_ids)
        return self.get(url)

    def get_events(self, _type, **kwargs):
        url = urljoin("events/", _type)
        res = self.get(url, params=kwargs)

        try:
            res.raise_for_status()
            data = res.json()
        except (HTTPError) as error:
            logger.error(f"Could not get orders: {error}")
            return []
        except (JSONDecodeError) as error:
            logger.error(f"Could not decode response JSON: {error}")
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
                logger.error(f"Could not get orders on page {page}: {error}")
                yield []
            except (JSONDecodeError) as error:
                logger.error(f"Could not decode response JSON on page {page}: "
                             f"{error}")
                yield []
            yield data.get("events")


    def get_orders(self, **kwargs):
        res = self.get("orders", params=kwargs)

        try:
            res.raise_for_status()
            data = res.json()
        except (HTTPError) as error:
            logger.error(f"Could not get orders: {error}")
            return []
        except (JSONDecodeError) as error:
            logger.error(f"Could not decode response JSON: {error}")
            return []

        yield data.get("orders", [])

        while data.get("nextPage"):
            page = data.get("nextPage")
            res = self.get("orders", params={**kwargs, "page":page})
            try:
                res.raise_for_status()
                data = res.json()
            except (HTTPError) as error:
                logger.error(f"Could not get orders on page {page}: {error}")
                yield []
            except (JSONDecodeError) as error:
                logger.error(f"Could not decode response JSON on page {page}: "
                             f"{error}")
                yield []
            yield data.get("orders")

    def get_parents(self, with_bundles=False):
        """Get information about "parent" products and their children

        Keyword Arguments:
            with_bundles {bool} -- Control whether bundles are
                                   whitelisted (default: {False})

        Returns:
            [dict] -- A dict with parent id as key and a list of
                      children as value
        """
        products = []
        res = self.get_products_list()

        try:
            res.raise_for_status()
            json_data = res.json()
            products.extend(json_data.get("products", []))
        except (HTTPError) as error:
            logger.error(f"Could not get products list: {error}")
            return {}
        except (JSONDecodeError) as error:
            logger.error(f"Could not decode response JSON: {error}")
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
            logger.error(f"Could not get product data: {error}")
            return {}
        except (JSONDecodeError) as error:
            logger.error(f"Could not decode response JSON: {error}")
            return {}

        parent_information = defaultdict(list)
        for info in data:
            offers = info.get("offers", [])

            blacklist = []
            if not(with_bundles):
                blacklist.append("bundle")

            #skip if blacklisted
            blacklisted = False
            for offer in offers:
                if offer.get("type") in blacklist:
                    blacklisted = True

            if blacklisted:
                continue

            #this must be the child of *some* product
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
            logger.error(f"Could not mark event processed: {error}")
        return res