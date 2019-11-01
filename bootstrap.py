from collections import defaultdict
from os import environ, remove
from os.path import exists
from pathlib import Path

from yaml import safe_load, dump, YAMLError

from . import logger
from .models import Product
from .sessions import FastSpring

def products(include_path=False):
    """Get product information from the products dir

    Keyword Arguments:
        include_path {bool} -- Also include the path for each product
                               definition (default: {False})

    Returns:
        [dict] -- A dict with the layout {name: {info}}
    """
    path = Path(__file__).parent / "products"

    products = {}
    for file in path.glob("*.yaml"):
        with open(file) as f:
            try:
                info = safe_load(f)
                name = info.get("name")
                if name is not None:
                    if include_path:
                        info["path"] = info.get("path", file.resolve())
                    products[name] = info
            except (YAMLError, AttributeError) as error:
                logger.error(f"Could not load {file.resolve()}: {error}. "
                             "Is it malformed?")
    return products

def fs_update_yaml_definitions():
    """Update yaml defines per the current state of FastSpring"""

    logger.info("Updating YAML definitions per FastSpring.")

    parent_info = FastSpring(close=True).get_parents()
    for _, info in products(include_path=True).items():
        for alias in info.get("aliases", []):
            if alias in parent_info:
                #check the new set of definitions
                #against the old set of definitions
                _new = set(parent_info[alias])
                _old = set(info.get("aliases", []))
                if _new.issubset(_old):
                    logger.debug(f"Skipping {info.get('name')}")
                    continue

                logger.info(f"Updating {info.get('name')}")
                info["aliases"] = parent_info[alias]

                #the parent product is also an alias
                if not(alias in info["aliases"]):
                    info["aliases"].append(alias)

                path = info.get("path", "")
                with open(path, "w") as f:
                    info.pop("path")
                    dump(info, f)
    new_defs = products()
    return new_defs

def bootstrap():
    
    logger.info("Bootstrapping engine and products")

    #first past the post gets to create the engine
    from .engine import TheEngine

    fs_update_yaml_definitions()

    session = TheEngine.new_session()
    for name, info in products().items():
            product = session.query(Product).\
                        filter_by(name=name).first()
            if not(product):
                bl = ["legacy_aliases"]

                try:
                    [info.pop(i) for i in bl]
                except (KeyError):
                    pass

                product = Product(**info)
                logger.info(f"Created new product: {product.name}")
            elif product:
                bl = ["name", "legacy_aliases"]
                [setattr(product, k, v) for k, v in info.items() if not(k in bl)]
            session.add(product)
    if len(session.dirty) > 0 or len(session.new) > 0:
        session.commit()
    TheEngine.remove()
    logger.info("Finished bootstrapping process.")