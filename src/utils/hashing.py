import hashlib

from src.core.models import Product
from src.utils.xml_helpers import clean_html_text


def product_hash(product: Product) -> str:
    normalized_description = clean_html_text(product.description_html or "", max_len=4000)
    base = "|".join([
        product.item_id,
        (product.title or "").strip(),
        normalized_description,
        (product.category_text or "").strip(),
        (product.variant_text() or "").strip(),
    ])
    return hashlib.md5(base.encode("utf-8")).hexdigest()
