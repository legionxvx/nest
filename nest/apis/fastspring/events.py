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
    """Base class for all webhook events of a FastSpring API Webhook
    event.

    If a session is provided, most of the properties will be valid new
    or existing database objects. Otherwise, the properties are the
    parsed webhook event data.
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
        """The resulting database object, if any.
        """
        raise NotImplementedError("Derived classes must implement this.")

    @abstractmethod
    def is_order(self):
        """True if webhook type is ``'order.completed'``.
        """
        return self.type == "order.completed"

    @abstractmethod
    def is_return(self):
        """True if webhook type is ``'return.created'``.
        """
        return self.type == "return.created"

    @abstractmethod
    def is_subscription_activated(self):
        """True if webhook type is ``'subscription.activated'``.
        """
        return self.type == "subscription.activated"

    @abstractmethod
    def is_subscription_deactivated(self):
        """True if webhook type is ``'subscription.deactivated'``.
        """
        return self.type == "subscription.deactivated"

    @abstractmethod
    def convert(self, subclass):
        """Convert this ``WebhookEvent`` into a more refined subclass.

        Data and database session are passed to subclass' constructor.

        :param subclass: The derived class of a ``WebhookEvent``.
        """
        return subclass(self.raw, self.session)

    @abstractmethod
    def to_order(self):
        """Convert this ``WebhookEvent`` to an
        :class:`~nest.apis.fastspring.events.Order`.
        """
        return self.convert(Order)

    @abstractmethod
    def to_return(self):
        """Convert this ``WebhookEvent`` to a
        :class:`~nest.apis.fastspring.events.Return`.
        """
        return self.convert(Return)

    @abstractmethod
    def to_subscription(self, active):
        """Convert this ``WebhookEvent`` to an
        :class:`~nest.apis.fastspring.events.SubscriptionActivated` or
        :class:`~nest.apis.fastspring.events.SubscriptionDeactivated`.
        """
        if active:
            return self.convert(SubscriptionActivated)
        return self.convert(SubscriptionDeactivated)

    def __repr__(self):
        return f"<Event type='{self.type}' id='{self.id}'>"

class Order(WebhookEvent):
    def __init__(self, data={}, session=None):
        super().__init__(data, type_hint="order.completed")
        self.session = session or self.session

        self._customer = None
        self._recipients = None
        self._products = None
        self._model = None

    @property
    def customer(self):
        """The user/customer who paid for these items.
        """
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
        """The list of users for whom these items are propogated to.

        Since FastSpring allows gifting of purchases, this list could,
        theoretically, be infinitely long. However, for the time
        being, we assume that the first recipient is the actual
        intended recipient of this purchase. Typically, this is also
        the :class:`~nest.apis.fastspring.events.Order.customer`.
        """
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
        """True if the intended recipient is not the purchaser.
        """
        if len(self.recipients) > 1:
            self.logger.warning(
                "Cannot determine gift with multiple recipients."
            )

        if len(self.recipients) == 1:
            if self.session:
                if self.customer != self.recipients[0]:
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
        """The list of products in this order.
        """
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
        """List of product paths or ids of the parent or triggering
        items of this order.
        """
        paths = []
        for item in self.data.get("items", []):
            path = item.get("driver", {}).get("path")
            if path:
                paths.append(path)
        return paths

    @property
    def total(self):
        """Order amount total in USD.
        """
        return self.data.get("totalInPayoutCurrency", 0)

    @property
    def discount(self):
        """Total discount amount in USD.
        """
        return self.data.get("discountInPayoutCurrency", 0)

    @property
    def model(self):
        """Constructed database
        :class:`~nest.engines.psql.models.Order` object.
        """
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
    def __init__(self, data={}, session=None):
        super().__init__(data, type_hint="return.created")
        self.session = session

        self._order = None
        self._model = None

    @property
    def order(self):
        """The original order this return belongs to.
        """
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
        """Constructed database
        :class:`~nest.engines.psql.models.Return` object.
        """
        if not(self._model):
            args = {
                "reference": self.data.get("reference"),
                "amount": self.data.get("totalReturnInPayoutCurrency", 0)
            }
            self._model = models.Return(**args)
        return self._model

# @ToDo -> Condense these into their own `SubscriptionEvent` sub-class
class SubscriptionActivated(WebhookEvent):
    def __init__(self, data={}, session=None):
        super().__init__(data, type_hint="subscription.activated")
        self.session = session

        self._user = None

    @property
    def user(self):
        """The user who subscribed.
        """
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
    def __init__(self, data={}, session=None):
        super().__init__(data, type_hint="subscription.deactivated")
        self.session = session

        self._user = None

    @property
    def user(self):
        """The user who unsubscribed.
        """
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
