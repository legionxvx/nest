from os import environ
from urllib.parse import urljoin
from collections import defaultdict

from requests import Session

class FastSpring(Session):
    """Custom session with FastSpring's API prefixed"""
    def __init__(self, prefix=None, close=False, hooks={}, **kwargs):
        self.prefix = prefix or "https://api.fastspring.com/products"

        super().__init__(**kwargs)

        self.hooks = hooks
        self.auth = (environ.get("FS_AUTH_USER"), environ.get("FS_AUTH_PASS"))

        if close:
            self.headers.update({'Connection':'close'})

    def request(self, method, url, *args, **kwargs):
        _url = urljoin(self.prefix, url)
        return super().request(method, _url, *args, **kwargs)

    def get_products_list(self):
        return self.get("products")

    def get_products(self, products):
        """Get information for one or more prodcuts
        
        Arguments:
            products {list} -- Product ID's
        """
        joined_ids = ",".join(products)
        return self.get(f"products/{joined_ids}")
    
    def get_parents(self, with_bundles=False):
        """Get information about "parent" products and their children
        
        Keyword Arguments:
            with_bundles {bool} -- Control whether bundles are 
                                   whitelisted (default: {False})
        
        Returns:
            [dict] -- A dict with parent id as key and a list of 
                      children as value
        """
        products = []
        res = self.get_products_list()
        res.raise_for_status()

        if res.ok:
            try:
                json_data = res.json()
                products.extend(json_data.get("products", []))
            except:
                pass

        if len(products) == 0:
            return {}

        res = self.get_products(products)
        res.raise_for_status()

        data = []
        if res.ok:
            try:
                json_data = res.json()
                data.extend(json_data.get("products", []))
            except:
                pass

        parent_information = defaultdict(list)
        for info in data:
            offers = info.get("offers", [])

            blacklist = []
            if not(with_bundles):
                blacklist.append("bundle")

            #skip if blacklisted
            blacklisted = False
            for offer in offers:
                if offer.get("type") in blacklist:
                    blacklisted = True

            if blacklisted:
                continue

            #this must be the child of *some* product
            parent = info.get("parent")
            child = info.get("product")
            if parent and child:
                parent_information[parent].append(child)

        return parent_information