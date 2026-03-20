import hashlib

from src.core.models import Product
from src.utils.xml_helpers import clean_html_text


def _normalize_text(value: str) -> str:
    return " ".join((value or "").strip().split())


def _normalized_variant_text(product: Product) -> str:
    pairs = [
        (_normalize_text(param.name), _normalize_text(param.value))
        for param in product.params
        if (param.name or "").strip() or (param.value or "").strip()
    ]
    pairs.sort(key=lambda item: (item[0].casefold(), item[1].casefold()))
    return "|".join(f"{name}:{value}" for name, value in pairs)


def product_hash(product: Product) -> str:
    normalized_description = _normalize_text(clean_html_text(product.description_html or "", max_len=4000))
    base = "|".join([
        _normalize_text(product.item_id),
        _normalize_text(product.title),
        normalized_description,
        _normalize_text(product.category_text),
        _normalized_variant_text(product),
    ])
    return hashlib.md5(base.encode("utf-8")).hexdigest()
