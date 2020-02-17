import logging
from abc import abstractproperty
from datetime import datetime
from json import load

from .. import logger
from ..engines.psql import models


class EventParser(object):
    def __init__(self, segment=[], type_hint=None):
        self.segment = segment
        self.type_hint = type_hint

    def __iter__(self):
        for data in self.segment:
            event = WebhookEvent(data, type_hint=self.type_hint)

            if event.is_order():
                yield Order(data)

            elif event.is_return():
                yield Return(data)

            elif event.is_subscription_activated():
                yield SubscriptionActivated(data)

            elif event.is_subscription_deactivated():
                yield SubscriptionDeactivated(data)

class WebhookEvent(object):
    def __init__(self, data={}, type_hint=None):
        for key in ["id", "live", "processed", "type", "created", "data"]:
            setattr(self, key, data.get(key))

        self.id = data.get("id", "")
        self.live = data.get("live", False)
        self.processed = data.get("processed", False)
        self.type = data.get("type", type_hint)
        self.created = data.get("created", datetime.utcnow())

        if self.created is not None:
            if isinstance(self.created, int):
                self.created = datetime.utcfromtimestamp(self.created // 1000)

        self.data = data.get("data", {})

    @abstractproperty
    def model(self):
        raise NotImplementedError("Derived classes must implement this.")

    def is_order(self):
        return self.type == "order.completed"

    def is_return(self):
        return self.type == "return.created"

    def is_subscription_activated(self):
        return self.type == "subscription.activated"

    def is_subscription_deactivated(self):
        return self.type == "subscription.deactivated"

    def __repr__(self):
        return f"<Event type='{self.type}' id='{self.id}'>"

class Order(WebhookEvent):

    def __init__(self, data={}):
        super().__init__(data)
        self.type = "order.completed"

        self.products = []
        for item in self.get("items", []):
            self.products.append(item.get("product", "NO NAME"))

    @property
    def model(self):
        created = datetime.utcnow()
        if hasattr(self, "created"):
            #FS timestamps have milliseconds
            created = datetime.utcfromtimestamp(self.created // 1000)

        paths = []
        for item in self.get("items", []):
            path = item.get("driver", {}).get("path")
            if path:
                paths.append(path)

        gift = False
        if self.get("customer", {}).get("email") != self.recipient.email:
            gift = True

        kwargs = {
            "reference": self.get("reference"),
            "created": created,
            "live": self.live,
            "gift": gift,
            "total": self.get("totalInPayoutCurrency", 0),
            "discount": self.get("discountInPayoutCurrency", 0),
            "paths": paths,
            "coupons": self.get("coupons", []),
        }
        return models.Order(**kwargs)

    @property
    def recipient(self):
        #for now there is only one recipient for every order
        #including gift purchases. Should this change, you
        #may want to turn this property into a list
        recipient = self.get("recipients", [{}])[0]
        info = recipient.get("recipient", {})
        address = info.get("address", {})

        kwargs = {
            "email": info.get("email"),
            "first": info.get("first", "John"),
            "last": info.get("last", "Doe"),
            "language_code": self.get("language", "en"),
            "country_code": address.get("country", "US"),
        }

        return models.User(**kwargs)

    def update_existing_order(self, order):
        order.reference = self.model.reference
        order.created = self.model.created
        order.live = self.model.live
        order.total = self.model.total
        order.discount = self.model.discount
        order.paths = self.model.paths
        order.coupons = self.model.coupons
        return order

    def update_existing_recipient(self, recipient):
        recipient.email = self.recipient.email
        recipient.first = self.recipient.first
        recipient.last = self.recipient.last
        recipient.language_code = self.recipient.language_code
        recipient.country_code = self.recipient.country_code
        return recipient

    def __repr__(self):
        return f"<Order id='{self.id}' order='{self.model}' recipients='{self.recipient}'>"

class Return(WebhookEvent):

    def __init__(self, data={}):
        super().__init__(data)
        self.type = "return.created"

        self.products = []
        for item in self.get("items", []):
            self.products.append(item.get("product", "NO NAME"))

    @property
    def model(self):
        original = self.get("original", {})
        kwargs = {
            "reference": original.get("reference")
        }
        return models.Return(**kwargs)

    @property
    def order(self):
        original = self.get("original", {})

        original_total = original.get("totalInPayoutCurrency", 0)
        return_total = self.get("totalReturnInPayoutCurrency", 0)
        new_total = original_total - return_total
        
        kwargs = {
            "reference": original.get("reference"),
            "created": datetime.utcnow(),
            "live": original.get("live", False),
            "gift": False,
            "total": new_total,
            "discount": original.get("discountInPayoutCurrency", 0),
            "paths": [],
            "coupons": [],
        }
        return models.Order(**kwargs)

    def update_existing_order(self, order):
        order.reference = self.order.reference
        order.total = self.order.total
        return order

class SubscriptionActivated(WebhookEvent):
    
    def __init__(self, data={}):
        super().__init__(data)
        self.type = "subscription.activated"
    
    @property
    def model(self):
        account = self.get("account", {})
        contact = account.get("contact")
        kwargs = {
            "email": contact.get("email"),
            "first": contact.get("first", "John"),
            "last": contact.get("last", "Doe"),
            "language_code": account.get("language", "en"),
            "country_code": account.get("country", "US"),
        }
        return models.User(**kwargs)

    def __repr__(self):
        return f"<SubscriptionActivated id='{self.id}' user='{self.model}'>"

class SubscriptionDeactivated(WebhookEvent):
    
    def __init__(self, data={}):
        super().__init__(data)
        self.type = "subscription.deactivated"
    
    @property
    def model(self):
        account = self.get("account", {})
        contact = account.get("contact")
        kwargs = {
            "email": contact.get("email"),
            "first": contact.get("first", "John"),
            "last": contact.get("last", "Doe"),
            "language_code": account.get("language", "en"),
            "country_code": account.get("country", "US"),
        }
        return models.User(**kwargs)

    def __repr__(self):
        return f"<SubscriptionDeactivated id='{self.id}' user='{self.model}'>"
