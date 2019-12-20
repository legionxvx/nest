import logging
from collections import defaultdict
from os import environ, remove
from os.path import exists
from pathlib import Path

from yaml import YAMLError, dump, safe_load

from ..engine import TheEngine
from ..models import Product
from .session import FastSpring

from . import logger

def get_products(include_path=False, include_legacy_aliases=False):
    path = Path(__file__).parent / "products"

    products = {}
    def get_info(file):
        info = {}
        with open(file, "r") as f:
            try:
                info = safe_load(f)
            except (YAMLError, AttributeError) as error:
                logger.error(f"Could not load {file.resolve()}: {error}")
        
        name = info.get("name")
        
        if not(isinstance(name, str)):
            logger.error(f"Cannot use name of {type(name)}")
            return

        if include_path:
            info["path"] = info.get("path", file.resolve())
            
        if include_legacy_aliases:
            aliases = info.get("aliases", [])
            legacy = info.pop("legacy_aliases", [])
            
            if len(legacy) > 0:
                logger.info(f"{name} -> legacy aliases: {legacy}")
                aliases.extend(legacy)

            info["aliases"] = aliases
        
        products[name] = info

    for file in path.glob("*.yaml"):
        get_info(file)

    for file in path.glob("*.yml"):
        get_info(file)

    return products

def update_definitions():
    fs = FastSpring()
    if not(fs.connected):
        logger.info("Skipping definition update: Cannot connect to FastSpring")
        return get_products()

    parents = fs.get_parents()
    products = get_products(include_path=True)
    
    for _, info in products.items():
        aliases = info.get("aliases", [])
        for alias in aliases:
            if not(alias in parents):
                continue

            name = info.get("name")

            #check the new set of definitions
            #against the old set of definitions
            children = parents[alias]
            
            _new = set(children)
            _old = set(aliases)
            if _new.issubset(_old):
                logger.debug(f"Skipping {name}")
                continue

            logger.info(f"Updating {name}")
            info["aliases"] = children

            #the parent product is also an alias
            if not(alias in aliases):
                info["aliases"].append(alias)

            #write this back to the file
            path = info.get("path", "")
            with open(path, "w") as f:
                info.pop("path")
                dump(info, f)
    return get_products()

def bootstrap():
    if not(TheEngine.connected):
        logger.critical("Skipping Bootstrap: The engine is not connected.")
        return False
    
    session = TheEngine.new_session()
    products = update_definitions()
    
    for name, info in products.items():
        product = session.query(Product).filter_by(name=name).first()
        if not(product):
            bl = ["legacy_aliases"]
            [info.pop(i, None) for i in bl]

            product = Product(**info)
            logger.info(f"Created new product: {product.name}")
        else:
            bl = ["name", "legacy_aliases"]
            [setattr(product, k, v) for k, v in info.items() if not(k in bl)]
        
        session.add(product)

    if len(session.dirty) > 0 or len(session.new) > 0:
        session.commit()
    TheEngine.remove()
    return True