from config import Stable as config

from sqlalchemy import (
        Column, Integer, Boolean,
        Text, DateTime, Float, 
        ARRAY, ForeignKey, func, 
        case, cast, select,
        distinct
    )

from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.orm import relationship

#specific PostgreSQL dialect types and functions
from sqlalchemy.dialects.postgresql.json import JSONB
from sqlalchemy.dialects.postgresql import array_agg

#engine/metadata creation
from sqlalchemy.engine.url import URL
from sqlalchemy.sql import text
from sqlalchemy import create_engine, and_

from datetime import datetime, timedelta
from json import loads

with open(config.PRODUCTS_JSON_PATH, 'r') as f:
    products = loads(f.read())
    products.pop('_comment')

paid_products = {name: True for name, data in products.items() \
                if data.get('price', 0) > 0}

previous_mixbus = {name: True for name, data in products.items() \
                   if (data.get('set', '') == 'Mixbus') and not(data.get('current', True))}

current_mixbus = {name: True for name, data in products.items() \
                  if data.get('set', '') == 'Mixbus' and data.get('current', True)}

previous_32c = {name: True for name, data in products.items() \
                if (data.get('set', '') == '32C') and not(data.get('current', True))}

current_32c = {name: True for name, data in products.items() \
               if data.get('set', '') == '32C' and data.get('current', True)}

default_products = {name: False for name in products}

#create our mapping
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    #columns
    id                 = Column(Integer, primary_key=True)
    email              = Column(Text, unique=True, nullable=False)
    first              = Column(Text)
    last               = Column(Text)
    country_code       = Column(Text, default='US')
    language_code      = Column(Text, default='en')
    date_created       = Column(DateTime, default=datetime.utcnow())
    last_token_request = Column(DateTime)

    #relationships
    orders         = relationship('Order', backref='user', cascade='save-update')

    #hybrid properties ----------------------------------------------------------------------------
    """Hybrid properties can be both quieried on the database AND be
    run on our object after it has been loaded (queried).

    Each hyrid property needs (in most cases) a complimentary expression
    if you want to query the database using it. The expressions I've made
    are quite hacky, but seem to be working.

    E.g after user has been queried:

        user = session.query(User).filer_by(email="foobar@baz.net").first()
        if user.current_member:
            print("Hooray!")

    Eg. querying users based on property:

        for user in session.query(User).filter(User.current_member):
            print("Hooray!")
    """


    """Current Member (Defunct) - True if any order.items contains 
    'Plugged-In Membership' *and* order.date is less than 30 days ago,
    else False
    Usage - User.current_member
    """

    @hybrid_property
    def current_member(self):
        for order in self.orders:
            if order.items.get('Plugged-In Membership'):
                month_ago = datetime.now() - timedelta(days=30)
                if order.date >= month_ago:
                    return True
        return False

    @current_member.expression
    def current_member(cls):
        month_ago = datetime.now() - timedelta(days=30)

        statement = select([True]).\
                        where(Order.user_id == cls.id).\
                        where(Order.items.contains({'Plugged-In Membership':True})).\
                        where(Order.date >= month_ago)
        return statement.label('current_member')

    "Products - Aggregate Array of *distinct* order.items keys"
    "Usage - User.products"
    
    @hybrid_property
    def products(self):
        products = []
        for order in self.orders:
            for item, owned in order.items.items():
                if not(item in products) and owned:
                    products.append(item)
        return products

    @products.expression
    def products(cls):
        #postgres array_agg return type, not standard
        _xpr = array_agg(distinct(text("keys")))
        statement = select([_xpr]).\
                        where(Order.user_id == cls.id).\
                            select_from(text("jsonb_object_keys(items) as keys"))
        return statement.label('products')

    "Product Count - count() of *distinct* order.items keys"
    "Usage - User.product_count"
    
    @hybrid_property
    def product_count(self):
        items = []
        for order in self.orders:
            for item, owned in order.items.items():
                if not(item in items) and owned:
                    items.append(item)
        return len(items)

    @product_count.expression
    def product_count(cls):
        _xpr = func.count(distinct(text("keys")))
        statement = select([_xpr]).\
                        where(Order.user_id == cls.id).\
                            select_from(text("jsonb_object_keys(items) as keys"))
        return statement.label('product_count')

    "Owns Any Paid - True if any order.value > 0, else False"
    "Usage - User.owns_any_paid"

    @hybrid_property
    def owns_any_paid(self):
        for item in self.products:
            if item in paid_products:
                return True
        return False

    @owns_any_paid.expression
    def owns_any_paid(cls):
        return case(
            [
                (User.orders.any(Order.items.contains({k:v})), True) for k,v in paid_products.items()
            ], 
            else_=False
        )

    "Owns Previous Mixbus - True if any order.items has a previous_mixbus key in it, else False"
    "Usage - User.owns_previous_mixbus"

    @hybrid_property
    def owns_previous_mixbus(self):
        for order in self.orders:
            for item, owned in order.items.items():
                if (item in previous_mixbus) and (owned):
                    return True
        return False

    @owns_previous_mixbus.expression
    def owns_previous_mixbus(cls):
        return case(
            [
                (User.orders.any(Order.items.contains({k:v})), True) for k,v in previous_mixbus.items()
            ],
            else_=False
        )

    "Owns Current Mixbus - True if any order.items has current_mixbus in it"
    "Usage - User.owns_current_mixbus"

    @hybrid_property
    def owns_current_mixbus(self):
        for order in self.orders:
            for item, owned in order.items.items():
                if (item in current_mixbus) and (owned):
                    return True
        return False

    @owns_current_mixbus.expression
    def owns_current_mixbus(cls):
        return case(
            [
                (User.orders.any(Order.items.contains(current_mixbus)), True)
            ],
            else_=False
        )   

    "Owns Previous 32C - True if any order.items has a previous_32c key in it"
    "Usage - User.owns_previous_32c"

    @hybrid_property
    def owns_previous_32c(self):
        for order in self.orders:
            for item, owned in order.items.items():
                if (item in previous_32c) and (owned):
                    return True
        return False

    @owns_previous_32c.expression
    def owns_previous_32c(cls):
        return case(
            [
                (User.orders.any(Order.items.contains({k:v})), True) for k,v in previous_32c.items()
            ],
            else_=False
        )

    "Owns Current 32C - True if any order.items has a current_32c key in it"
    "Usage - User.owns_current_32c"

    @hybrid_property
    def owns_current_32c(self):
        for order in self.orders:
            for item, owned in order.items.items():
                if (item in current_32c) and (owned):
                    return True
        return False

    @owns_current_32c.expression
    def owns_current_32c(cls):
        return case(
            [
                (User.orders.any(Order.items.contains(current_32c)), True)
            ],
            else_=False
        )

    "Misc"

    @hybrid_property
    def latest_order_date(self):
        return max([order.date for order in self.orders])

    @latest_order_date.expression
    def latest_order_date(cls):
        _xpr = func.max(Order.date)
        return select([_xpr]).where(Order.user_id == cls.id).label('max_date')

    @hybrid_property
    def earliest_order_date(self):
        if len(self.orders) > 0:
            return min([order.date for order in self.orders])
        else:
            return datetime.date(1970, 1, 1)

    @earliest_order_date.expression
    def earliest_order_date(cls):
        _xpr = func.min(Order.date)
        return select([_xpr]).where(Order.user_id == cls.id).label('min_date')

    @hybrid_property
    def order_count(self):
        return len(self.orders)

    @order_count.expression
    def order_count(cls):
        _xpr = func.count(Order.id)
        return select([_xpr]).where(Order.user_id == cls.id).label('order_count')

    @hybrid_property
    def total_spent(self):
        total = 0
        for order in self.orders:
            total += order.total
        return total

    @total_spent.expression
    def total_spent(cls):
        _xpr = func.sum(Order.total)
        return select([_xpr]).where(Order.user_id == cls.id).label('total_spent')

    @hybrid_property
    def average_spent(self):
        total = 0
        for order in self.orders:
            total += order.total
        return total / len(self.orders)

    @average_spent.expression
    def average_spent(cls):
        _xpr = func.avg(Order.total)
        return select([_xpr]).where(Order.user_id == cls.id).label('average_spent')
    
    #end hybrid properties ------------------------------------------------------------------------

    def hashed_email(self, alg):
        return alg(self.email.encode()).hexdigest()
    
    def craft_mcp_payload(self, resource_status):
        if resource_status == 404:
            #Post request, new user
            
            payload = {
                    'email_address': self.email,
                    'status': 'subscribed',
                    'language': self.language_code,
                    'merge_fields': {'FNAME':self.first, 'LNAME':self.last},
                    'tags': []
                }

            for product in self.products:
                payload['tags'].append(product)
            
            if self.earliest_order_date > (datetime.now() - timedelta(1)):
                if not(self.owns_any_paid):
                    payload['tags'].append('drip-victim')
            
            if ('Mixbus32C v5 Demo' in self.products) or ('Mixbus v5 Demo' in self.products):
                payload['tags'].append('Some Mixbus Demo')

            return payload, {}

        if resource_status == 200:
            #Patch request for regular info, and Post request for tags

            payload = {
                'language': self.language_code,
                'merge_fields': {'FNAME':self.first, 'LNAME':self.last}
            }

            tags  = [{'name':product, 'status':'active'} \
            for product in self.products]
            
            tags += [{'name':product, 'status':'inactive'} \
            for product in default_products if not(product in self.products)]
            
            if not(len(self.products) >= 1):
                tags += [{'name':'No-items', 'status':'active'}]
            else:
                tags += [{'name':'No-items', 'status':'inactive'}]

            if ('Mixbus32C v5 Demo' in self.products) or ('Mixbus v5 Demo' in self.products):
                tags += [{'name':'Some Mixbus Demo', 'status':'active'}]
            
            return payload, {'tags':tags}

    def __repr__(self):
        var_text = ", ".join(["'%s'='%s'" % (k, v) for k,v in vars(self).items()])
        return "<User(%s)>\n" % var_text

class Order(Base):
    __tablename__ = 'orders'

    #columns
    id             = Column(Integer, primary_key=True)
    reference      = Column(Text, unique=True, nullable=False)
    timestamp      = Column(Integer, nullable=False)
    date           = Column(DateTime, nullable=False)
    total          = Column(Float, default=0.0)
    discount       = Column(Float, default=0.0)
    fullfillment   = Column(JSONB, default={})
    items          = Column(JSONB, default={})
    path           = Column(Text)
    coupon         = Column(Text)

    #relationships
    user_id        = Column(Integer, ForeignKey('users.id', onupdate="cascade", ondelete="cascade"), index=True)

    @hybrid_property
    def item_count(self):
        return len(self.items)

    @item_count.expression
    def item_count(cls):
        _xpr = func.count()
        statement = select([_xpr]).\
                        select_from(text('jsonb_each(items)')).\
                            where(Order.id == cls.id)
        return statement.label('item_count')

    @hybrid_property
    def utc_time(self):
        return datetime.utcfromtimestamp(self.timestamp)

    @hybrid_property
    def office_time(self):
        return datetime.fromtimestamp(self.timestamp)

    def __repr__(self):
        var_text = ", ".join(["'%s'='%s'" % (k, v) for k,v in vars(self).items()])
        return "<Order(%s)>" % var_text

engine = create_engine(URL(**config.POSTGRESQL_DB_INFO), echo=config.PGSQL_ECHO)
Base.metadata.create_all(engine)