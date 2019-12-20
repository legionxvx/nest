from datetime import datetime, timedelta
from hashlib import md5
from json import JSONDecodeError, dumps
from os import environ
from urllib.parse import urljoin

from flask import current_app
from requests import HTTPError, Session

from ..fastspring.events import Order
from ..fastspring.utils import get_products
from ..models import User
from .. import logger


class Mailchimp(Session):
    """Bootstrapped connection to Mailchimp's API using our
    credentials"""
    def __init__(self, auth=None, prefix=None, close=False, hooks={}, **kwargs):
        self.prefix = prefix or "https://us14.api.mailchimp.com/3.0/"
        self.lists = {}

        super().__init__(**kwargs)

        self.auth = auth or (
                        environ.get("MAILCHIMP_AUTH_USER", "foo"),
                        environ.get("MAILCHIMP_AUTH_TOKEN", "bar")
                    )
        self.hooks = hooks

        if close:
            self.headers.update({'Connection':'close'})

        self.get_lists()
        self.default_list = self.lists.get(environ.get("MAILCHIMP_LIST"))
        self.connected = self.get("/").ok

    @classmethod
    def hash_email(cls, email=""):
        return md5(email.encode()).hexdigest()

    def request(self, method, url, endpoint=None, list_id=None, default=True,
                *args, **kwargs):
        if default:
            if not(self.default_list):
                logger.error("Trying to request to Mailchimp "
                                        "with defaults, except there is no "
                                        "default list!")
            endpoint = endpoint or "members"
            list_id = list_id or self.default_list
            parts = ["lists", list_id, endpoint, url]
            url = urljoin(self.prefix, "/".join(parts))
        else:
            url = urljoin(self.prefix, url)
        return super().request(method, url, *args, **kwargs)

    def get_lists(self):
        """Create a map of list_name -> list_id

        Returns:
            [dict] -- Map of list_name -> list_id
        """
        res = self.get("lists", default=False)

        if res.ok:
            data = res.json()
            lists = data.get("lists", [])
            for list in lists:
                if list.get("name") and list.get("id"):
                    self.lists.update({list.get("name"): list.get("id")})
        return self.lists

    def get_members(self, list_id=None, **kwargs):
        offset = 0
        res = self.get("", list_id=list_id, params=kwargs)

        try:
            res.raise_for_status()
            data = res.json()
        except (HTTPError) as error:
            logger.error(f"Could not get orders: {error}")
            return []
        except (JSONDecodeError):
            logger.error(f"Could not decode response JSON: {error}")
            return []

        members = data.get("members", [])
        yield members

        total = data.get("total_items")
        offset += len(members)
        while offset < total:
            try:
                res = self.get("", list_id=list_id, params={**kwargs,
                           "offset":offset})
                res.raise_for_status()
                data = res.json()
            except (HTTPError) as error:
                logger.error(f"Could not get orders: {error}")
                yield []
            except (JSONDecodeError):
                logger.error(f"Could not decode response JSON: "
                                         f"{error}")
                yield []

            members = data.get("members", [])
            yield members
            offset += len(members)

    def get_member(self, email=None, from_user=None, list_id=None):
        """Get the member resource located on a given list

        The email is md5 hashed and then requested from :list_id:

        Keyword Arguments:
            email {str} -- Email string (default: {None})

            from_user {nest.models.User} -- A User object
                                            (default: {None})

            list_id {str} -- The list_id to request from
                             (default: {None})

        Raises:
            Exception: If neither :email: nor :from_user: are specified
            TypeError: If :from_user: is not a valid type

        Returns:
            [requests.models.Response] -- The repsonse to the GET
                                          request
        """
        if not(email or from_user):
            raise Exception("Must specify an email or user object to check.")

        if from_user:
            if not(isinstance(from_user, User)):
                raise TypeError(f"Cannot get member from {type(from_user)}.")

        resource = self.hash_email(email or from_user.email)

        return self.get(resource, list_id=list_id)

    def unsubscribe_member(self, email=None, from_user=None, list_id=None):
        """Unsubscribe the member resource located on a given list

        The email is md5 hashed and then requested form :list_id:

        Keyword Arguments:
            email {str} -- Email string (default: {None})

            from_user {nest.models.User} -- A User object
                                            (default: {None})

            list_id {str} -- The list_id to request from
                             (default: {None})

        Raises:
            Exception: If neither :email: nor :from_user: are specified
            TypeError: If :from_user: is not a valid type

        Returns:
            [requests.models.Response] -- The repsonse to the GET
                                          request
        """
        if from_user:
            if not(isinstance(from_user, User)):
                raise TypeError(f"Cannot unsubscibe user of {type(from_user)}.")

        payload = {'status': 'unsubscribed',}

        resource = self.hash_email(email or from_user.email)

        return self.patch(resource, data=dumps(payload), list_id=list_id)

    def create_user(self, user, list_id=None):
        """Create a list member

        Arguments:
            user {nest.models.User} -- The User object to create

        Raises:
            TypeError: If :user: is not a valid type

        Returns:
            [requests.Models.Response] -- The repsonse to the POST
                                          request
        """
        if not(isinstance(user, User)):
            raise TypeError(f"Cannot create user from {type(user)}.")

        payload = {
            'email_address': user.email,
            'status': 'subscribed',
            'language': user.language_code,
            'merge_fields': {'FNAME':user.first, 'LNAME':user.last},
            'tags': []
        }

        for product in user.products:
            payload["tags"].append(product.name)

        #remove returns
        for order in user.orders:
            if len(order.returns) > 0:
                for product in order.products:
                    try:
                        idx = payload["tags"].index(product.name)
                        payload["tags"].pop(idx)
                    except:
                        pass

        if user.earliest_order_date > (datetime.utcnow() - timedelta(days=1)):
            if not(user.owns_any_paid):
                payload['tags'].append('drip-victim')

        res = self.post("", data=dumps(payload), list_id=None)
        if not(res.ok):
            logger.error(f"Could not create user @ {list_id} - "
                                     f"{res.content}")
        return res

    def update_user(self, user, list_id=None):
        """Update a list member's information and tags

        Arguments:
            user {nest.models.User} -- The User object to update

        Raises:
            TypeError: If :user: is not a valid type

        Returns:
            [tuple] -- PATCH and POST responses
        """
        if not(isinstance(user, User)):
            raise TypeError(f"Cannot user user from {type(user)}.")

        payload = {
            'language': user.language_code,
            'merge_fields': {'FNAME':user.first, 'LNAME':user.last}
        }

        resource = self.hash_email(user.email)

        owned_product_names = [product.name for product in user.products]

        tags = [{'name':item.name, 'status':'active'} for item in user.products]
        tags.extend([{'name':item, "status":"inactive"} for item in \
            get_products()
        if not item in owned_product_names])

        if not(len(user.products) >= 1):
            tags.extend([{'name':'No-items', 'status':'active'}])
        else:
            tags.extend([{'name':'No-items', 'status':'inactive'}])

        patch = self.patch(resource, data=dumps(payload), list_id=list_id)
        post  = self.post(f"{resource}/tags", data=dumps({"tags":tags}),
                          list_id=list_id)

        return (patch, post)
