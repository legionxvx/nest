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

            product = session.query(Product).\
                        filter_by(name=info.get("name")).first()

            if not(product):
                product = Product(**info)
            elif product:
                bl = ["name"]
                [setattr(product, k, v) for k, v in info.items() if not(k in bl)]
            session.add(product)
    session.commit()
    TheEngine.remove()