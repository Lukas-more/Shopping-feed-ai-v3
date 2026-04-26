from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path

from src.core.models import Product

UNKNOWN_MARGIN_LABEL = "m-x"
MARGIN_LABEL_ORDER = ("m-x", "m-s", "m-m", "m-l", "m-xl")


def _parse_decimal(value: object) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text.replace("\xa0", "").replace(" ", "").replace(",", ".")
    try:
        return float(normalized)
    except ValueError:
        return None


def _classify_margin(margin: float) -> str:
    if margin < 50:
        return "m-s"
    if margin < 150:
        return "m-m"
    if margin < 300:
        return "m-l"
    return "m-xl"


def _build_default_margin_map(products: list[Product]) -> tuple[dict[str, str], dict[str, int]]:
    labels = {product.item_id: UNKNOWN_MARGIN_LABEL for product in products}
    stats = {
        "purchase_csv_rows_loaded": 0,
        "purchase_csv_rows_skipped": 0,
        "products_with_purchase_price": 0,
        "products_missing_purchase_price": len(products),
        "label_m_x": len(products),
        "label_m_s": 0,
        "label_m_m": 0,
        "label_m_l": 0,
        "label_m_xl": 0,
    }
    return labels, stats


def _load_csv_rows(path: Path) -> list[dict[str, str]]:
    raw_bytes = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp1250", "iso-8859-2"):
        try:
            text = raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
        return list(csv.DictReader(StringIO(text)))
    raise UnicodeDecodeError("purchase_prices_csv", raw_bytes, 0, 1, "Unsupported CSV encoding")


def load_purchase_price_labels(products: list[Product], csv_path: str) -> tuple[dict[str, str], dict[str, int]]:
    labels, stats = _build_default_margin_map(products)
    if not csv_path:
        return labels, stats

    path = Path(csv_path)
    if not path.exists():
        return labels, stats

    purchase_prices: dict[str, float | None] = {}

    try:
        rows = _load_csv_rows(path)
    except (OSError, UnicodeDecodeError, csv.Error):
        return labels, stats

    for row in rows:
        code = (row.get("code") or "").strip()
        if not code:
            stats["purchase_csv_rows_skipped"] += 1
            continue

        purchase_price_raw = (row.get("purchasePrice") or "").strip()
        purchase_price = _parse_decimal(purchase_price_raw)
        if purchase_price_raw and purchase_price is None:
            stats["purchase_csv_rows_skipped"] += 1
            continue

        stats["purchase_csv_rows_loaded"] += 1
        purchase_prices[code] = purchase_price

    stats["products_missing_purchase_price"] = 0
    stats["label_m_x"] = 0

    for product in products:
        feed_price = _parse_decimal(product.price_vat)
        purchase_price = purchase_prices.get(product.item_id)
        if feed_price is None or purchase_price is None:
            labels[product.item_id] = UNKNOWN_MARGIN_LABEL
            stats["products_missing_purchase_price"] += 1
            stats["label_m_x"] += 1
            continue

        margin = feed_price - purchase_price - 70 - (feed_price * 0.05)
        label = _classify_margin(margin)
        labels[product.item_id] = label
        stats["products_with_purchase_price"] += 1
        if label == "m-s":
            stats["label_m_s"] += 1
        elif label == "m-m":
            stats["label_m_m"] += 1
        elif label == "m-l":
            stats["label_m_l"] += 1
        else:
            stats["label_m_xl"] += 1

    return labels, stats
