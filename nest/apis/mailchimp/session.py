import logging
from hashlib import md5
from os import environ
from urllib.parse import urljoin

from requests import Session

from nest.apis.utils import protect


class Mailchimp(Session):
    """A custom ``Session`` to interact with Mailchimp's API.
    """
    def __init__(self, auth=None, hooks={}):
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
        """A dict of Mailchimp list names to internal list ids.
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

        This property is the **name** of the list, which will be
        extracted from :class:`~nest.apis.Mailchimp.lists`.
        """
        return self.__default_list

    @default_list.setter
    def default_list(self, new):
        self.__default_list = new

    @classmethod
    def md5(cls, message):
        """Hash a message with md5.
        """
        if isinstance(message, bytes):
            return md5(message).hexdigest()
        elif isinstance(message, str):
            return md5(message.encode()).hexdigest()

    @classmethod
    def multijoin(cls, url, *parts, seperator="/"):
        """Like ``urllib.parse.urljoin()``, except it takes a variable
        number of args and a variable seperator.

        :param url: URL to prefix join to.
        :param parts: Positional list of parts to join.
        :param seperator: Seperator to join parts to.
        """
        return urljoin(url, seperator.join(parts))

    def request(self, method, suffix, *args, **kwargs):
        """A normal request except that the
        :class:`~nest.apis.Mailchimp.prefix` and suffix are joined to
        create the endpoint.

        The list id for this request defaults to
        :class:`~nest.apis.Mailchimp.default_list`.

        :param method: HTTP Request method.
        :param suffix: Joined to :class:`~nest.apis.Mailchimp.prefix`.
        :param args: Other positional arguments passed to request.
        :param kwargs: Other keyword arguments passed to request. If
            ``list`` is included in kwargs, it will popped and used in
            place of the :class:`~nest.apis.Mailchimp.default_list`
        """
        id = kwargs.pop(
            "list",
            self.lists.get(self.default_list, "")
        )
        endpoint = self.multijoin(self.prefix, "lists", id, suffix)
        return super().request(method, endpoint, *args, **kwargs)

    @protect(default=[])
    def get_members(self, *args, **kwargs):
        """Yields members of a list.

        :param args: Other positional arguments passed to each ``GET``
            request.
        :param kwargs: Other keyword arguments passed to each ``GET``
            request.
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
        """Yield a specific member of a list by email.

        :param email: The email of the member
        :param args: Other positional arguments passed to ``GET``
            request.
        :param kwargs: Other keyword arguments passed to ``GET``
            request.
        """
        res = self.get(f"members/{self.md5(email)}", *args, **kwargs)
        res.raise_for_status()
        data = res.json()
        return data
