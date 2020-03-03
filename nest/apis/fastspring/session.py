import logging
from collections import defaultdict
from os import environ
from urllib.parse import urljoin

from requests import Session

from nest.apis.utils import protect


class FastSpring(Session):
    """A custom ``Session`` to interact with FastSpring's API.
    """
    def __init__(self, prefix=None, auth=None, hooks={}):
        super().__init__()
        self.logger = logging.getLogger("nest")
        self.hooks = hooks
        self.auth = auth or (
            environ.get("FS_AUTH_USER", ""),
            environ.get("FS_AUTH_PASS", "")
        )

    @property
    def prefix(self):
        """URL to prefix on all requests. Since this is dedicated to
        FastSpring, it is (currently): 'https://api.fastspring.com'.

        This property is *read-only* and has no setter.
        """
        return "https://api.fastspring.com"

    def request(self, method, suffix, *args, **kwargs):
        """Just like a normal ``Session.request()`` except that the 
        ``url`` is constructed using ``prefix`` and ``suffix``

            :param method: HTTP Verb
            :param suffix: Appended to ``prefix``
            :param *args: Passed to ``super`` request method
            :param **kwargs: Passed to ``super`` request method
        """
        endpoint = urljoin(self.prefix, suffix)
        return super().request(method, endpoint, *args, **kwargs)

    @protect(default={})
    def get_products(self, filter=[], blacklist=[], *args, **kwargs):
        """Request the "products" endpoint.

        The ``products`` endpoint returns information about products
        like their parents, price, offerings, description etc.

            :param filter=[]: List of product id's
            :param blacklist=[]: Offer type blacklist, useful for
            removing things like bundles
            :param *args: Passed to each ``get()`` request
            :param **kwargs: Passed to each ``get()`` request
        """
        # Endpoint accepts comma-seperated list of product names
        joined_ids = ",".join(filter)
        res = self.get(f"products/{joined_ids}", *args, **kwargs)
        res.raise_for_status()
        data = res.json()

        # `Filter` must've been empty, do the same request with the
        # list of product ids in response
        if len(data) > 1:
            joined_ids = ",".join(data.get("products", []))
            res = self.get(f"products/{joined_ids}", *args, **kwargs)
            res.raise_for_status()
            data = res.json()

        # Stitch together the information
        products = defaultdict(dict)
        for info in data.get("products", []):
            if info.get("result") != "success":
                continue

            if len(blacklist) > 0:
                offers = info.get("offers", [])
                # Skip offer-types in blacklist
                if any([offer.get("type") in blacklist for offer in offers]):
                    continue

            pricing = info.get("pricing", {})
            price = pricing.get("price", {})
            alias = info.get("product")
            parent = info.get("parent")

            # If there is no parent for this product, the alias must
            # be the product itself
            if not(parent):
                parent = alias
                products[parent]["price"] = price.get("USD", 0)

            if parent and alias:
                info = products[parent]
                info["aliases"] = info.get("aliases", [])
                info["aliases"].append(alias)

        return products

    @protect(default=[])
    def get_events(self, type, *args, **kwargs):
        """Request to the "events" endpoint.

        The events endpoint allows you to retrieve previous webhook
        events and process them again (or in some cases for the first)
        time.

            :param type: "processed" or "unprocessed"
            :param *args: Passed to each ``get()`` request
            :param **kwargs: Passed to each ``get()`` request
        """
        res = self.get(f"events/{type}", *args, **kwargs)
        res.raise_for_status()
        data = res.json()

        for event in data.get("events", []):
            yield event

        # Drop any 'days' from params - it breaks the next request
        kwargs["params"] = kwargs.get("params", {})
        kwargs["params"].pop("days", None)

        while data.get("more"):
            # Change "begin" param to the last order timestamp
            events = data.get("events", [{}])
            timestamp = events[-1].get("created")
            if not(timestamp):
                break

            kwargs["params"].update(begin=timestamp+1)
            res = self.get(f"events/{type}", *args, **kwargs)

            res.raise_for_status()
            data = res.json()
            
            for event in data.get("events", []):
                yield event

    @protect(default=[])
    def get_orders(self, *args, **kwargs):
        """Request to the "orders" endpoint.

        The "orders" endpoint gives you information about orders
        including those with returns. This is useful for bulk imports.

            :param *args: Passed to each ``get()`` request
            :param **kwargs: Passed to each ``get()`` request
        """
        res = self.get("orders", *args, **kwargs)
        res.raise_for_status()
        data = res.json()

        for order in data.get("orders", []):
            yield order

        kwargs["params"] = kwargs.get("params", {})

        while data.get("nextPage"):
            page = data.get("nextPage")
            kwargs["params"].update(page=page)
            res = self.get("orders", **kwargs)

            res.raise_for_status()
            data = res.json()
            
            for order in data.get("orders", []):
                yield order

    @protect(default={})
    def update_event(self, id, *args, **kwargs):
        """Requests POST to the "events" endpoint

        Typically you want to use this to mark an event as "processed".

            :param id: The event's id
            :param *args: Passed to ``post()`` request
            :param **kwargs: Passed to ``post()`` request
        """
        res = self.post(f"events/{id}", *args, **kwargs)
        res.raise_for_status()
        return res.json()
