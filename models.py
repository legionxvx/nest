from datetime import datetime, timedelta

from sqlalchemy import (
    Column,
    Integer,
    Boolean,
    Text,
    DateTime,
    Float,
    ForeignKey,
    select,
    distinct,
    func,
    not_,
    and_
)

from sqlalchemy.dialects.postgresql.array import ARRAY
from sqlalchemy.dialects.postgresql import array_agg
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.schema import Sequence
from sqlalchemy.orm import relationship

Base = declarative_base()

class OrderProductAssociation(Base):
    __tablename__ = "order_product_associations"
    order_id = Column(
        Integer,
        ForeignKey("orders.id", onupdate="cascade", ondelete="cascade"),
        primary_key=True
    )
    product_id = Column(
        Integer,
        ForeignKey("products.id", onupdate="cascade", ondelete="cascade"),
        primary_key=True
    )

class User(Base):
    __tablename__ = "users"

    id                 = Column(Integer, primary_key=True)
    email              = Column(Text, unique=True, nullable=False)
    first              = Column(Text)
    last               = Column(Text)
    country_code       = Column(Text, default="US")
    language_code      = Column(Text, default="en")
    created            = Column(DateTime, default=datetime.utcnow())
    last_token_request = Column(DateTime)

    orders   = relationship("Order", backref="user", cascade="save-update")

    @hybrid_property
    def products(self):
        products = []
        for order in self.orders:
            if len(order.returns) != 0:
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
                        where(not_(Order.id.in_(select([Return.order_id])))).\
                        where(Order.id == OrderProductAssociation.order_id).\
                        where(Product.id == OrderProductAssociation.product_id)
        return statement.label('products')

    @hybrid_property
    def earliest_order_date(self):
        if len(self.orders) > 0:
            return min([order.date for order in self.orders])
        return datetime(1970, 1, 1)

    @earliest_order_date.expression
    def earliest_order_date(cls):
        _xpr = func.min(Order.date)
        return select([_xpr]).where(Order.user_id == cls.id).label('min_date')

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
                        where(Order.id == OrderProductAssociation.order_id).\
                        where(Product.id == OrderProductAssociation.product_id).\
                            where(Product.price > 0)
        return statement.label("any-paid")

    @hybrid_property
    def owns_any_ava(self):
        return any([product.set == "AVA" for product in self.products])

    @owns_any_ava.expression
    def owns_any_ava(cls):
        statement = select([True]).\
                        where(Order.user_id == cls.id).\
                        where(Order.id == OrderProductAssociation.order_id).\
                        where(Product.id == OrderProductAssociation.product_id).\
                            where(Product.set == "AVA")
        return statement.label("any-ava")

    @hybrid_property
    def owns_any_mixbus(self):
        return any([product.set == "Mixbus" for product in self.products])

    @owns_any_mixbus.expression
    def owns_any_mixbus(cls):
        statement = select([True]).\
                        where(Order.user_id == cls.id).\
                        where(Order.id == OrderProductAssociation.order_id).\
                        where(Product.id == OrderProductAssociation.product_id).\
                            where(Product.set == "Mixbus")
        return statement.label("any-mixbus")

    @hybrid_property
    def owns_current_mixbus(self):
        for product in self.products:
            if product.set == "Mixbus" and product.current:
                return True
        return False

    @owns_current_mixbus.expression
    def owns_current_mixbus(cls):
        statement = select([True]).\
                        where(Order.user_id == cls.id).\
                        where(Order.id == OrderProductAssociation.order_id).\
                        where(Product.id == OrderProductAssociation.product_id).\
                            where(and_(Product.set == "Mixbus", Product.current))
        return statement.label("any-current-mixbus")

    @hybrid_property
    def owns_any_32c(self):
        return any([product.set == "32C" for product in self.products])

    @owns_any_32c.expression
    def owns_any_32c(cls):
        statement = select([True]).\
                        where(Order.user_id == cls.id).\
                        where(Order.id == OrderProductAssociation.order_id).\
                        where(Product.id == OrderProductAssociation.product_id).\
                            where(Product.set == "32C")
        return statement.label("any-32c")

    @hybrid_property
    def owns_current_32c(self):
        for product in self.products:
            if product.set == "32C" and product.current:
                return True
        return False

    @owns_current_32c.expression
    def owns_current_32c(cls):
        statement = select([True]).\
                        where(Order.user_id == cls.id).\
                        where(Order.id == OrderProductAssociation.order_id).\
                        where(Product.id == OrderProductAssociation.product_id).\
                            where(and_(Product.set == "32C", Product.current))
        return statement.label("any-current-32c")

    @hybrid_property
    def highest_version_of_mixbus(self):
        m_versions = [0]
        for product in self.products:
            if product.set == "Mixbus":
                m_versions.append(product.version)
        return max(m_versions)

    @highest_version_of_mixbus.expression
    def highest_verison_of_mixbus(cls):
        statement = select([func.max(Product.version)]).\
                        where(Order.user_id == cls.id).\
                        where(Order.id == OrderProductAssociation.order_id).\
                        where(Product.id == OrderProductAssociation.product_id).\
                            where(Product.set == "Mixbus")
        return statement.label("highest-mixbus-version")

    @hybrid_property
    def highest_version_of_32c(self):
        c_versions = [0]
        for product in self.products:
            if product.set == "32C":
                c_versions.append(product.version)
        return max(c_versions)

    @highest_version_of_32c.expression
    def highest_verison_of_32c(cls):
        statement = select([func.max(Product.version)]).\
                        where(Order.user_id == cls.id).\
                        where(Order.id == OrderProductAssociation.order_id).\
                        where(Product.id == OrderProductAssociation.product_id).\
                            where(Product.set == "32C")
        return statement.label("highest-32c-version")

class Order(Base):
    __tablename__ = "orders"

    id        = Column(Integer, primary_key=True)
    reference = Column(Text, unique=True, nullable=False)
    created   = Column(DateTime, nullable=False)
    date      = Column(DateTime, nullable=False)
    live      = Column(Boolean, nullable=False)
    total     = Column(Float, default=0.0)
    discount  = Column(Float, default=0.0)
    path      = Column(Text)
    coupon    = Column(Text)
    name      = Column(Text)

    user_id = Column(
        Integer,
        ForeignKey("users.id", onupdate="cascade", ondelete="cascade"),
        index=True
    )
    products = relationship("Product", secondary="order_product_associations",
                            back_populates="orders", cascade="save-update")

    returns = relationship("Return", back_populates="order",
                           cascade="save-update")

    def __repr__(self):
        return f"<Order reference='{self.reference}'>"

class Return(Base):
    __tablename__ = "returns"

    id = Column(Integer, Sequence("returns_seq"), primary_key=True)
    reference = Column(Text, unique=True, nullable=False)

    order_id = Column(
        Integer,
        ForeignKey("orders.id", onupdate="cascade", ondelete="cascade"),
        primary_key=True
    )
    order = relationship("Order", back_populates="returns",
                         cascade="save-update")

    def __repr__(self):
        return f"<Return for='{self.reference}'>"

class Product(Base):
    __tablename__ = "products"

    id      = Column(Integer, primary_key=True)
    name    = Column(Text, unique=True, nullable=False)
    aliases = Column(ARRAY(Text, dimensions=1), nullable=False)
    price   = Column(Float, nullable=False)
    set     = Column(Text, nullable=False)
    version = Column(Integer)
    signer  = Column(Text)
    token   = Column(Text)
    part    = Column(Text)
    current = Column(Boolean)

    orders = relationship("Order", secondary="order_product_associations",
                          back_populates="products", cascade="save-update")

    def __repr__(self):
        return f"<Product name='{self.name}'>"