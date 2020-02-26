from datetime import datetime, timedelta
from hashlib import md5

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    and_,
    or_,
    distinct,
    func,
    not_,
    select,
    DECIMAL
)

from sqlalchemy.dialects.postgresql import array_agg
from sqlalchemy.dialects.postgresql.array import ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Sequence

Base = declarative_base()

class OrderProductAssociation(Base):
    """docstring here

        :param order_id:
        :param product_id:
    """
    __tablename__ = "order_product_associations"

    order_id = Column(
        Integer,
        ForeignKey(
            "orders.id",
            onupdate="cascade",
            ondelete="cascade"
        ),
        primary_key=True
    )

    product_id = Column(
        Integer,
        ForeignKey(
            "products.id",
            onupdate="cascade",
            ondelete="cascade"
        ),
        primary_key=True
    )

class User(Base):
    """docstring here

        :param id:
        :param email:
        :param first:
        :param last:
        :param country_code:
        :param language_code:
        :param created:
        :param last_token_request:
        :param subscribed:

        :param orders:

        :param products:
        :param earliest_order_date:
    """
    __tablename__ = "users"

    id                 = Column(Integer, primary_key=True)
    email              = Column(Text, unique=True, nullable=False)
    first              = Column(Text, nullable=False)
    last               = Column(Text, nullable=False)
    country_code       = Column(Text, nullable=False, default="US")
    language_code      = Column(Text, nullable=False, default="en")
    created            = Column(DateTime, nullable=False, default=datetime.utcnow())
    last_token_request = Column(DateTime, nullable=False, default=datetime.utcfromtimestamp(0))
    subscribed         = Column(Boolean, nullable=False, default=False)

    orders = relationship(
        "Order",
        backref="user",
        cascade="save-update"
    )

    def __repr__(self):
        _hash = md5(self.email.encode()).hexdigest()
        return f"<User hash='{_hash}'>"

    @hybrid_property
    def products(self):
        products = []
        for order in self.orders:
            if order.returned:
                continue

            for product in order.products:
                if not(product in products):
                    products.append(product)
        return products

    @products.expression
    def products(cls):
        _xpr = array_agg(distinct(Product.name))
        statement = select([_xpr]).\
                        where(Order.user_id == cls.id).\
                        where(or_(Order.returned == None, not_(Order.returned))).\
                        where(Order.id == OrderProductAssociation.order_id).\
                        where(Product.id == OrderProductAssociation.product_id)
        return statement.label('products')

    @hybrid_property
    def earliest_order_date(self):
        if len(self.orders) > 0:
            return min([order.date for order in self.orders])
        return datetime.utcfromtimestamp(0)

    @earliest_order_date.expression
    def earliest_order_date(cls):
        _xpr = func.min(Order.date)
        return select([_xpr]).where(Order.user_id == cls.id).label('min-date')

    @hybrid_property
    def owns_any_paid(self):
        for order in self.orders:
            for product in order.products:
                if product.price > 0:
                    return True
        return False

    @owns_any_paid.expression
    def owns_any_paid(cls):
        statement = select([True]).\
                        where(Order.user_id == cls.id).\
                        where(or_(Order.returned == None, not_(Order.returned))).\
                        where(Order.id == OrderProductAssociation.order_id).\
                        where(Product.id == OrderProductAssociation.product_id).\
                        where(Product.price > 0)
        return statement.label("any-paid")

    @hybrid_method
    def owns_any_in_set(self, value):
        """docstring here

            :param value:
        """
        for product in self.products:
            if product.set == value:
                return True
        return False

    @owns_any_in_set.expression
    def owns_any_in_set(cls, value):
        statement = select([True]).\
                    where(Order.user_id == cls.id).\
                    where(or_(Order.returned == None, not_(Order.returned))).\
                    where(Order.id == OrderProductAssociation.order_id).\
                    where(Product.id == OrderProductAssociation.product_id).\
                    where(and_(Product.set == value, not_(Product.demo)))
        return statement.label(f"owns-any-{value}")

    @hybrid_method
    def owns_current_in_set(self, value):
        """docstring here

            :param value:
        """
        for product in self.products:
            if product.set == value and product.current and not(product.demo):
                return True
        return False

    @owns_current_in_set.expression
    def owns_current_in_set(cls, value):
        statement = select([True]).\
                        where(Order.user_id == cls.id).\
                        where(or_(Order.returned == None, not_(Order.returned))).\
                        where(Order.id == OrderProductAssociation.order_id).\
                        where(Product.id == OrderProductAssociation.product_id).\
                        where(and_(Product.set == value, Product.current, not_(Product.demo)))
        return statement.label(f"any-current-{value}")

    @hybrid_method
    def highest_version_in_set(self, value):
        """docstring here

            :param value:
        """
        m_versions = [0]
        for product in self.products:
            if product.set == value and not(product.demo):
                m_versions.append(product.version)
        return max(m_versions)

    @highest_version_in_set.expression
    def highest_version_in_set(cls, value):
        statement = select([func.max(Product.version)]).\
                        where(Order.user_id == cls.id).\
                        where(or_(Order.returned == None, not_(Order.returned))).\
                        where(Order.id == OrderProductAssociation.order_id).\
                        where(Product.id == OrderProductAssociation.product_id).\
                        where(and_(Product.set == value, not_(Product.demo)))
        return statement.label(f"highest-version-of-{value}")

class Order(Base):
    """docstring here

        :param id:
        :param reference:
        :param created:
        :param date:
        :param live:
        :param gift:
        :param total:
        :param discount:
        :param paths:
        :param coupons:
        :param name:

        :param user_id:
        :param products:
        :param returns:

        :param returned:
    """
    __tablename__ = "orders"

    id        = Column(Integer, primary_key=True)
    reference = Column(Text, unique=True, nullable=False)
    created   = Column(DateTime, nullable=False, default=datetime.utcnow())
    date      = Column(DateTime, nullable=False, default=datetime.utcnow())
    live      = Column(Boolean, nullable=False, default=False)
    gift      = Column(Boolean, nullable=False, default=False)
    total     = Column(DECIMAL(precision=10, scale=2), nullable=False, default=0)
    discount  = Column(DECIMAL(precision=10, scale=2), nullable=False, default=0)
    paths     = Column(ARRAY(Text, dimensions=1), default=[])
    coupons   = Column(ARRAY(Text, dimensions=1), default=[])
    name      = Column(Text, nullable=False, default="John Doe")

    user_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            onupdate="cascade",
            ondelete="cascade"
        ),
        index=True
    )

    products = relationship(
        "Product",
        secondary="order_product_associations",
        back_populates="orders",
        cascade="save-update"
    )

    returns = relationship(
        "Return",
        back_populates="order",
        cascade="save-update"
    )

    @hybrid_property
    def returned(self):
        if len(self.returns) == 0:
            return False

        returned_total = 0
        for ret in self.returns:
            if not(ret.partial):
                return True
            returned_total += ret.amount

        return returned_total >= self.total

    @returned.expression
    def returned(cls):
        statement = select([func.sum(Return.amount)]).\
                        where(Return.order_id == cls.id) \
                            >= cls.total
        return statement.label("order-returned")

    def __repr__(self):
        return f"<Order reference='{self.reference}'>"

class Return(Base):
    """docstring here

        :param id:
        :param reference:
        :param amount:

        :param order_id:
        :param order:

        :param partial:
    """
    __tablename__ = "returns"

    id        = Column(Integer, primary_key=True)
    reference = Column(Text, nullable=False)
    amount    = Column(Integer, nullable=False)

    order_id = Column(
        Integer,
        ForeignKey(
            "orders.id",
            onupdate="cascade",
            ondelete="cascade"
        ),
    )

    order = relationship(
        "Order",
        back_populates="returns",
        cascade="save-update"
    )

    @hybrid_property
    def partial(self):
        return self.amount < self.order.total

    @partial.expression
    def partial(cls):
        statement = cls.amount < select([Order.total]).\
                                    where(Order.id == cls.order_id)
        return statement.label("partial-return")

    def __repr__(self):
        return f"<Return for='{self.reference}'>"

class Product(Base):
    """docstring here

        :param id:
        :param name:
        :param aliases:
        :param price:
        :param set:
        :param version:
        :param signer:
        :param token:
        :param part:
        :param current:
        :param demo:

        :param orders:
    """
    __tablename__ = "products"

    id      = Column(Integer, primary_key=True)
    name    = Column(Text, unique=True, nullable=False)
    aliases = Column(ARRAY(Text, dimensions=1), nullable=False, default=[])
    price   = Column(DECIMAL(precision=10, scale=2), nullable=False, default=0)
    set     = Column(Text, nullable=False, default="")
    version = Column(Integer, nullable=False, default=1)
    signer  = Column(Text, nullable=False, default="")
    token   = Column(Text, nullable=False, default="")
    part    = Column(Text, nullable=False, default="")
    current = Column(Boolean, nullable=False, default=True)
    demo    = Column(Boolean, nullable=False, default=False)

    orders = relationship(
        "Order",
        secondary="order_product_associations",
        back_populates="products",
        cascade="save-update"
    )

    def __repr__(self):
        return f"<Product name='{self.name}'>"
