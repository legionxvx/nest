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
)

from sqlalchemy.dialects.postgresql.array import ARRAY
from sqlalchemy.dialects.postgresql import array_agg
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
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
            for product in order.products:
                if not(product.name in products):
                    products.append(product.name)
        return products

    @products.expression
    def products(cls):
        _xpr = array_agg(distinct(Product.name))
        statement = select([_xpr]).\
                        where(Order.user_id == cls.id).\
                        where(Order.id == OrderProductAssociation.order_id).\
                        where(Product.id == OrderProductAssociation.product_id)
        return statement.label('products')

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

    user_id = Column(
        Integer, 
        ForeignKey("users.id", onupdate="cascade", ondelete="cascade"), 
        index=True
    )
    products = relationship("Product", secondary="order_product_associations", 
                            back_populates="orders", cascade="save-update")

class Product(Base):
    __tablename__ = "products"

    id      = Column(Integer, primary_key=True)
    name    = Column(Text, unique=True, nullable=False)
    aliases = Column(ARRAY(Text, dimensions=1))

    orders = relationship("Order", secondary="order_product_associations", 
                          back_populates="products", cascade="save-update")