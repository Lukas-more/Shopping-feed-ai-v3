from __future__ import annotations
import numpy as np
from src.core.models import Product
from src.utils.xml_helpers import parse_cz_price


def compute_price_buckets(products: list[Product]) -> dict[str, str]:
    prices = [parse_cz_price(p.price_vat) for p in products if parse_cz_price(p.price_vat) > 0]
    if not prices:
        return {p.item_id: "price_unknown" for p in products}
    p30 = float(np.percentile(prices, 30))
    p70 = float(np.percentile(prices, 70))
    result: dict[str, str] = {}
    for p in products:
        price = parse_cz_price(p.price_vat)
        if price <= 0:
            bucket = "price_unknown"
        elif price <= p30:
            bucket = "price_low"
        elif price <= p70:
            bucket = "price_mid"
        else:
            bucket = "price_high"
        result[p.item_id] = bucket
    return result
