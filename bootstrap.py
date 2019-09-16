from pathlib import Path

from yaml import load

from .engine import TheEngine
from .models import Product

def bootstrap():
    path = Path() / "products"

    session = TheEngine.new_session()
    for file in path.glob("*.yaml"):
        with open(file) as f:
            try:
                info = load(f)
            except:
                continue

            product = session.query(Product).filter_by(name=info.get("name")).first()

            #create the product
            if not(product):
                product = Product(name=info.get("name"), aliases=info.get("aliases"))
                session.add(product)
            #update the product
            elif product:
                product.aliases = info.get("aliases")
            session.add(product)
    session.commit()