import logging
from abc import abstractmethod, abstractproperty
from datetime import datetime
from json import load

from nest.engines.psql import models


class EventParser(object):
    """Takes in a generator or other iterable object and spits 
    constructs appropriate WebhookEvent subclasses.

    Any session or type hinting passed to this will be forwarded to 
    resulting objects.
    """
    def __init__(self, generator, session=None, type_hint=None):
        self.generator = generator
        self.session = session
        self.type_hint = type_hint

    def __iter__(self):
        for data in self.generator:
            event = WebhookEvent(
                data, 
                session=self.session, 
                type_hint=self.type_hint
            )

            if event.is_order():
                yield event.to_order()
            
            elif event.is_return():
                yield event.to_return()
            
            elif event.is_subscription_activated():
                yield event.to_subscription(True)
            
            elif event.is_subscription_deactivated():
                yield event.to_subscription(False)
            else:
                yield event

class WebhookEvent(object):
    """An object representation of a FastSpring API Webhook event.

    If a session is provided, most of the properties will be valid new 
    or existing database objects.
    """
    def __init__(self, data={}, session=None, type_hint=None):
        self.id = data.get("id", "")
        self.live = data.get("live", False)
        self.processed = data.get("processed", False)
        self.type = data.get("type", type_hint)
        self.created = data.get("created", datetime.utcnow())
        self.logger = logging.getLogger("nest")

        if self.created is not None:
            if isinstance(self.created, int):
                self.created = datetime.utcfromtimestamp(self.created // 1000)

        self.raw = data
        self.data = data.get("data", {})
        self.session = session

        if type_hint and not(self.type == type_hint):
            self.logger.warning(
                f"Event type is '{self.type}', but was given type hint of: "
                f"'{type_hint}'; fallout from disparate types likely!"
            )

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

    @abstractmethod
    def convert(self, sub_class):
        return sub_class(self.raw, self.session)

    @abstractmethod
    def to_order(self):
        return self.convert(Order)

    @abstractmethod
    def to_return(self):
        return self.convert(Return)

    @abstractmethod
    def to_subscription(self, active):
        if active:
            return self.convert(SubscriptionActivated)
        return self.convert(SubscriptionDeactivated)

    def __repr__(self):
        return f"<Event type='{self.type}' id='{self.id}'>"

class Order(WebhookEvent):
    """Order webhook event.

        :param customer: The customer who purchased this order
        :param recipients: The list of recipients this order is going 
        to. Right now we only use the first recipient (usually the 
        customer) when constructing the model.
        :param gift: True if the customer is different than the 
        first recipient, else False
        :param products: The list of products in this order.
        :param paths: List of product path/if of the parent or 
        triggering item of the items in this order
        :param total: The order total in USD
        :param discount: The order discount in USD
        :param model: Resulting database ``Order`` object
    """
    def __init__(self, data={}, session=None):
        super().__init__(data, type_hint="order.completed")
        self.session = session or self.session

        self._customer = None
        self._recipients = None
        self._products = None
        self._model = None

    @property
    def customer(self):
        if not(self._customer):
            customer = self.data.get("customer", {})
            user = None
            if self.session:
                email = customer.get("email", "")
                query = self.session.query(models.User).filter_by(email=email)
                
                user = query.first()
                if not(user):
                    user = models.User(
                        email=email, 
                        first=customer.get("first", "John"),
                        last=customer.get("last", "Doe"),
                    )
            self._customer = user or customer
        return self._customer
    
    @property
    def recipients(self):
        if not(self._recipients):
            recipients = self.data.get("recipients", []).copy()
            for i, recipient in enumerate(recipients):
                info = recipient.get("recipient", {})
                email = info.get("email", "")
                if self.session:
                    query = self.session.query(models.User).\
                        filter_by(email=email)
                    user = query.first()
                    if user:
                        recipients[i] = user
                    else:
                        recipients[i] = models.User(
                            email=email, 
                            first=info.get("first", "John"),
                            last=info.get("last", "Doe"),
                        )
                else:
                    recipients[i] = info
            self._recipients = recipients
        return self._recipients
    
    @property
    def gift(self):
        if len(self.recipients) > 1:
            self.logger.error("Cannot determine gift with multiple recipients.")
        
        if len(self.recipients) == 1:
            if self.session:
                if self.customer == self.recipients[0]:
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
        if not(self._products):
            products = []
            for item in self.data.get("items", []):
                products.append(item.get("product", ""))
            
            if self.session:
                op = models.Product.aliases.overlap(products)
                query = self.session.query(models.Product).filter(op)
                products = query.all()
            self._products = products
        return self._products

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
        return self.data.get("totalInPayoutCurrency", 0)

    @property
    def discount(self):
        return self.data.get("discountInPayoutCurrency", 0)
    
    @property
    def model(self):
        if not(self._model):
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
            self._model = models.Order(**args)
        return self._model

    def __repr__(self):
        return (f"<Event (Order) id='{self.id}' "
                f"customer='{self.recipients[0]}' "
                f"recipients='{self.recipients}'>")

class Return(WebhookEvent):
    """Return webhook event.

        :param order: The original order this return is for
        :param model: Resulting database ``Return`` object
    """
    def __init__(self, data={}, session=None):
        super().__init__(data, type_hint="return.created")
        self.session = session

        self._order = None
        self._model = None

    @property
    def order(self):
        if not(self._order):
            original = self.data.get("original", {})
            reference = original.get("reference", "")
            if self.session:
                query = self.session.query(models.Order).filter_by(
                            reference=reference
                        )
                original = query.first()
            self._order = original
        return self._order

    @property
    def model(self):
        if not(self._model):
            args = {
                "reference": self.data.get("reference"),
                "amount": self.data.get("totalReturnInPayoutCurrency", 0)
            }
            self._model = models.Return(**args)
        return self._model

# @ToDo -> Condense these into their own `SubscriptionEvent` sub-class
class SubscriptionActivated(WebhookEvent):
    """Subscription Activation event

        :param user: The user this subscription is for
    """
    def __init__(self, data={}, session=None):
        super().__init__(data, type_hint="subscription.activated")
        self.session = session

        self._user = None

    @property
    def user(self):
        if not(self._user):
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
            self._user = user
        return user

class SubscriptionDeactivated(WebhookEvent):
    """Subscription Deactivation event

        :param user: The user this subscription is for
    """
    def __init__(self, data={}, session=None):
        super().__init__(data, type_hint="subscription.deactivated")
        self.session = session

        self._user = None
    
    @property
    def user(self):
        if not(self._user):
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
            self._user = user
        return self._user
