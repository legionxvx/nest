import logging
from hashlib import md5
from os import environ
from urllib.parse import urljoin

from requests import Session

from nest.apis.utils import protect


class Mailchimp(Session):
    """A custom ``Session`` to interact with Mailchimp's API.
    """
    def __init__(self, prefix=None, auth=None, hooks={}):
        super().__init__()
        self.logger = logging.getLogger("nest")
        self.hooks = hooks
        self.auth = auth or (
            environ.get("MAILCHIMP_AUTH_USER", ""),
            environ.get("MAILCHIMP_AUTH_TOKEN", "")
        )
        self._lists = None
        self.__default_list = None

    @property
    def lists(self):
        """A dict of Mailchimp 'lists' to their internal ids
        """   
        if not(self._lists):
            self._lists = {}
            url = urljoin(self.prefix, "lists")
            res = super().request("GET", url)
            res.raise_for_status()
            data = res.json()
            
            for info in data.get("lists", []):
                name = info.get("name")
                list_id = info.get("id")
                if info.get("name") and info.get("id"):
                    self._lists.update({name: list_id})
        return self._lists

    @property
    def prefix(self):
        """URL to prefix on all requests. Since this is dedicated to
        Mailchimp, it is (currently): 
        'https://us14.api.mailchimp.com/3.0/'.

        This property is *read-only* and has no setter.
        """
        return "https://us14.api.mailchimp.com/3.0/"

    @property
    def default_list(self):
        """Since most of this API usage is dedicated to maintaining 
        and modifying one list, this property acts as a default for 
        requests that do not specify a list id.
        """   
        return self.__default_list

    @default_list.setter
    def default_list(self, new):
        self.__default_list = new

    @classmethod
    def md5(cls, message):
        """Hash a message with md5.

        Useful, because all Mailchimp "resources" are md5 hashed 
        emails.

            :param message: 
        """   
        if isinstance(message, bytes):
            return md5(message).hexdigest()
        elif isinstance(message, str):
            return md5(message.encode()).hexdigest()

    @classmethod
    def multijoin(cls, url, *args, seperator="/"):
        """Like URL join, except it takes a variable number of args 
        and and a variable seperator.

            :param url: 
            :param *args: 
            :param seperator="/": 
        """   
        return urljoin(url, seperator.join(args))

    def request(self, method, suffix, *args, **kwargs):
        """Just like a normal ``Session.request()`` except that the 
        ``endpoint`` is constructed using ``prefix``, ``suffix``, 
        and ``list`` values.

        The list id for this request is extracted from kwargs. If a 
        ``default_list`` is present, the list id will default to that 
        list's id.

            :param method: HTTP Verb
            :param suffix: Appended to ``prefix``
            :param *args: Passed to ``super`` request method
            :param **kwargs: Passed to ``super`` request method
        """
        id = kwargs.pop(
            "list", 
            self.lists.get(self.default_list, "")
        )
        endpoint = self.multijoin(self.prefix, "lists", id, suffix)
        return super().request(method, endpoint, *args, **kwargs)

    @protect(default=[])
    def get_members(self, *args, **kwargs):
        """Get all members in a list.

            :param *args: Passed to each ``get()`` request
            :param **kwargs: Passed to each ``get()`` request
        """   
        res = self.get("members", *args, **kwargs)

        res.raise_for_status()
        data = res.json()

        members = data.get("members", [])
        for member in members:
            yield member
                
        total = data.get("total_items", 0)
        offset = len(members)
        kwargs["params"] = kwargs.get("params", {}) 
        while offset < total:
            kwargs["params"].update(offset=offset)
            res = self.get("members", *args, **kwargs)
            res.raise_for_status()
            data = res.json()
            members = data.get("members", [])
            for member in members:
                yield member
            offset += len(members)

    @protect(default={})
    def get_member(self, email, *args, **kwargs):
        """Get a specific member in a list by email.

            :param email: The email of the member
            :param *args: Passed to ``get()`` request
            :param **kwargs: Passed to ``get()`` request
        """   
        res = self.get(f"members/{self.md5(email)}", *args, **kwargs)
        res.raise_for_status()
        data = res.json()
        return data 
