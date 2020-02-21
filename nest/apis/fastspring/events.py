import logging
from abc import abstractmethod, abstractproperty
from datetime import datetime
from json import load

from nest import logger
from nest.engines.psql import models


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

    @abstractmethod
    def is_order(self):
        return self.type == "order.completed"

    @abstractmethod
    def is_return(self):
        return self.type == "return.created"

    @abstractmethod
    def is_subscription_activated(self):
        return self.type == "subscription.activated"

    @abstractmethod
    def is_subscription_deactivated(self):
        return self.type == "subscription.deactivated"

    def __repr__(self):
        return f"<Event type='{self.type}' id='{self.id}'>"

class Order(WebhookEvent):
    def __init__(self, data={}, session=None):
        super().__init__(data, type_hint="order.completed")
        self.session = session

        if not(self.type == "order.completed"):
            logger.warning(f"Constructed Order event is type: {self.type}, "
                           f"but should be type: 'order.completed'")

    @property
    def customer(self):
        customer = self.data.get("customer", {})
        if self.session:
            email = customer.get("email", "")
            query = self.session.query(models.User).filter_by(email=email)
            customer = query.first()
        return customer
    
    @property
    def recipients(self):
        recipients = self.data.get("recipients", []).copy()
        for i, recipient in enumerate(recipients):
            info = recipient.get("recipient", {})
            email = info.get("email", "")
            if self.session:
                query = self.session.query(models.User).filter_by(email=email)
                user = query.first()
                if user:
                    recipients[i] = user
            else:
                recipients[i] = info
        return recipients
    
    @property
    def gift(self):
        if len(self.recipients) > 1:
            logger.error("Cannot determine gift with multiple recipients.")
        
        if len(self.recipients) == 1:
            if self.session:
                if self.customer is not self.recipients[0]:
                    return True
            else:
                recipient = self.recipients[0].copy()
                recipient.pop("address", None)
                recipient.pop("account", None)
                if self.customer != recipient:
                    return True
        return False

    @property
    def products(self):
        products = []
        for item in self.data.get("items", []):
            products.append(item.get("product", ""))
        
        if self.session:
            op = models.Product.aliases.overlap(products)
            query = self.session.query(models.Product).filter(op)
            products = query.all()
        return products

    @property
    def paths(self):
        paths = []
        for item in self.data.get("items", []):
            path = item.get("driver", {}).get("path")
            if path:
                paths.append(path)
        return paths

    @property
    def total(self):
        return self.data.get("totalInPayoutCurrency", float(0))

    @property
    def discount(self):
        return self.data.get("discountInPayoutCurrency", float(0))
    
    @property
    def model(self):
        args = {
            "reference": self.data.get("reference"),
            "created": self.created,
            "live": self.live,
            "gift": self.gift,
            "total": self.total,
            "discount": self.discount,
            "paths": self.paths,
            "coupons": self.data.get("coupons", [])
        }

        if self.session:
            # @ToDo -> Handle multiple gift recipients
            args["products"] = self.products
            args["user"] = self.recipients[0]

        return models.Order(**args)

    def __repr__(self):
        return (f"<Event (Order) id='{self.id}' "
                f"customer='{self.recipients[0]}' "
                f"recipients='{self.recipients}'>")

class Return(WebhookEvent):
    def __init__(self, data={}, session=None):
        super().__init__(data, type_hint="return.created")
        self.session = session

        if not(self.type == "return.created"):
            logger.warning(f"Constructed Return event is type: {self.type}, "
                           f"but should be type: 'return.created'")

    @property
    def order(self):
        original = self.data.get("original", {})
        reference = original.get("reference", "")
        if self.session:
            query = self.session.query(models.Order).filter_by(
                        reference=reference
                    )
            original = query.first()
        return original

    @property
    def partial(self):
        refund_total = self.data.get("totalReturnInPayoutCurrency", float(0))
        original_total = 0

        if self.session:
            original_total = self.order.total
        else:
            original_total = self.order.get("totalInPayoutCurrency", float(0))
        
        return refund_total != original_total

    @property
    def model(self):
        reference = ""
        if self.session:
            reference = self.order.reference
        else:
            reference = self.order.get("reference", "")

        args = {
            "reference": reference,
            "partial": self.partial
        }
        return models.Return(**args)

# @ToDo -> Condense these into their own `SubscriptionEvent` sub-class
class SubscriptionActivated(WebhookEvent):    
    def __init__(self, data={}, session=None):
        super().__init__(data, type_hint="subscription.activated")
        self.session = session

        if not(self.type == "subscription.activated"):
            logger.warning(f"Constructed Return event is type: {self.type}, "
                           f"but should be type: 'subscription.activated'")

    @property
    def user(self):
        account = self.data.get("account", {})
        contact = self.data.get("contact", {})
        args = {
            "email": contact.get("email"),
            "first": contact.get("first", "John"),
            "last": contact.get("last", "Doe"),
            "language_code": account.get("language", "en"),
            "country_code": account.get("country", "US"),
        }

        user = None
        if self.session:
            email = contact.get("email")
            query = self.session.query(models.User).filter_by(email=email)
            user = query.first()

        user = user or models.User(**args)
        user.subscribed = self.data.get("active", False)
        return user

class SubscriptionDeactivated(WebhookEvent):
    def __init__(self, data={}, session=None):
        super().__init__(data, type_hint="subscription.deactivated")
        self.session = session

        if not(self.type == "subscription.deactivated"):
            logger.warning(f"Constructed Return event is type: {self.type}, "
                           f"but should be type: 'subscription.deactivated'")
    
    @property
    def user(self):
        account = self.data.get("account", {})
        contact = self.data.get("contact", {})
        args = {
            "email": contact.get("email"),
            "first": contact.get("first", "John"),
            "last": contact.get("last", "Doe"),
            "language_code": account.get("language", "en"),
            "country_code": account.get("country", "US"),
        }

        user = None
        if self.session:
            email = contact.get("email")
            query = self.session.query(models.User).filter_by(email=email)
            user = query.first()

        user = user or models.User(**args)
        user.subscribed = self.data.get("active", False)
        return user
