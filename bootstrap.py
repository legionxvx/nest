from pathlib import Path
from os import environ
from collections import defaultdict

from yaml import load, dump, FullLoader

from .engine import TheEngine
from .models import Product
from .sessions import FastSpring

def fs_update_yaml_definitions():
    """Update yaml defines per the current state of FastSpring"""
    fastspring = FastSpring()

    parent_info = fastspring.get_parents()

    path = Path(__file__).parent / "products"
    for file in path.glob("*.yaml"):
        with open(file, "r+") as f:
            try:
                info = load(f, Loader=FullLoader)
            except:
                continue

            for alias in info.get("aliases", []):
                if alias in parent_info:
                    info["aliases"] = parent_info[alias]

                    #the parent is also an alias
                    if not(alias in info["aliases"]):
                        info["aliases"].append(alias)

                    f.seek(0)
                    f.write("")
                    f.truncate()
                    dump(info, f)
                    break
    return products

def products():
    path = Path(__file__).parent / "products"

    products = []
    for file in path.glob("*.yaml"):
        with open(file) as f:
            try:
                info = load(f)
                name = info.get("name")
                if name is not None:
                    products.append(name)
            except:
                continue
    return products

def bootstrap():
    fs_update_yaml_definitions()
    path = Path(__file__).parent / "products"

    session = TheEngine.new_session()
    for file in path.glob("*.yaml"):
        with open(file) as f:
            try:
                info = load(f, Loader=FullLoader)
            except:
                continue

            product = session.query(Product).\
                        filter_by(name=info.get("name")).first()

            if not(product):
                product = Product(**info)
            elif product:
                bl = ["name", "legacy_aliases"]
                [setattr(product, k, v) for k, v in info.items() if not(k in bl)]
            session.add(product)
    session.commit()
    TheEngine.remove()