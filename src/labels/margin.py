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


def _normalize_code(value: object) -> str:
    text = " ".join(str(value or "").strip().split())
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


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
        "purchase_csv_present": 0,
        "purchase_csv_bytes": 0,
        "purchase_csv_looks_like_html": 0,
        "purchase_csv_encoding": "",
        "purchase_csv_delimiter": "",
        "purchase_csv_header_preview": [],
        "purchase_csv_row_count": 0,
        "purchase_csv_rows_loaded": 0,
        "purchase_csv_rows_skipped": 0,
        "purchase_csv_rows_with_purchase_price": 0,
        "purchase_csv_code_samples": [],
        "feed_id_samples": [_normalize_code(product.item_id) for product in products[:10]],
        "purchase_csv_match_count_exact": 0,
        "purchase_csv_match_count_normalized": 0,
        "products_matched_by_normalized_code": 0,
        "products_with_purchase_price": 0,
        "products_missing_purchase_price": len(products),
        "label_m_x": len(products),
        "label_m_s": 0,
        "label_m_m": 0,
        "label_m_l": 0,
        "label_m_xl": 0,
    }
    return labels, stats


def _looks_like_html(text: str) -> bool:
    sample = text.lstrip().lower()
    return sample.startswith("<!doctype html") or sample.startswith("<html") or sample.startswith("<head") or sample.startswith("<body")


def _detect_delimiter(sample: str) -> str:
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        return dialect.delimiter
    except csv.Error:
        counts = {
            ";": sample.count(";"),
            ",": sample.count(","),
            "\t": sample.count("\t"),
        }
        best = max(counts, key=counts.get)
        return best if counts[best] > 0 else ","


def _load_csv_rows(path: Path) -> tuple[list[dict[str, str]], str, str, list[str], int, int]:
    raw_bytes = path.read_bytes()
    if not raw_bytes:
        raise ValueError("Purchase prices CSV is empty")
    for encoding in ("utf-8-sig", "utf-8", "cp1250", "iso-8859-2"):
        try:
            text = raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
        if _looks_like_html(text):
            raise ValueError("Purchase prices download returned HTML instead of CSV")
        delimiter = _detect_delimiter(text[:4096])
        reader = csv.DictReader(StringIO(text), delimiter=delimiter)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])
        return rows, encoding, delimiter, fieldnames[:5], len(rows), len(raw_bytes)
    raise UnicodeDecodeError("purchase_prices_csv", raw_bytes, 0, 1, "Unsupported CSV encoding")


def load_purchase_price_labels(products: list[Product], csv_path: str) -> tuple[dict[str, str], dict[str, int]]:
    labels, stats = _build_default_margin_map(products)
    if not csv_path:
        return labels, stats

    path = Path(csv_path)
    if not path.exists():
        return labels, stats

    stats["purchase_csv_present"] = 1
    purchase_prices: dict[str, float | None] = {}
    purchase_prices_normalized: dict[str, float | None] = {}

    try:
        rows, encoding, delimiter, header_preview, row_count, byte_count = _load_csv_rows(path)
    except ValueError as exc:
        stats["purchase_csv_bytes"] = path.stat().st_size if path.exists() else 0
        if "HTML" in str(exc):
            stats["purchase_csv_looks_like_html"] = 1
        return labels, stats
    except (OSError, UnicodeDecodeError, csv.Error):
        return labels, stats

    stats["purchase_csv_encoding"] = encoding
    stats["purchase_csv_delimiter"] = {"\t": "\\t"}.get(delimiter, delimiter)
    stats["purchase_csv_header_preview"] = header_preview
    stats["purchase_csv_row_count"] = row_count
    stats["purchase_csv_bytes"] = byte_count

    for row in rows:
        code = _normalize_code(row.get("code"))
        if not code:
            stats["purchase_csv_rows_skipped"] += 1
            continue

        purchase_price_raw = (row.get("purchasePrice") or "").strip()
        purchase_price = _parse_decimal(purchase_price_raw)
        if purchase_price_raw and purchase_price is None:
            stats["purchase_csv_rows_skipped"] += 1
            continue

        stats["purchase_csv_rows_loaded"] += 1
        if purchase_price is not None:
            stats["purchase_csv_rows_with_purchase_price"] += 1
        if len(stats["purchase_csv_code_samples"]) < 10:
            stats["purchase_csv_code_samples"].append(code)
        purchase_prices[code] = purchase_price
        purchase_prices_normalized[_normalize_code(code)] = purchase_price

    stats["products_missing_purchase_price"] = 0
    stats["label_m_x"] = 0
    stats["purchase_csv_match_count_exact"] = sum(1 for product in products if _normalize_code(product.item_id) in purchase_prices)
    stats["purchase_csv_match_count_normalized"] = sum(1 for product in products if _normalize_code(product.item_id) in purchase_prices_normalized)

    for product in products:
        product_id = _normalize_code(product.item_id)
        feed_price = _parse_decimal(product.price_vat)
        purchase_price = purchase_prices.get(product_id)
        matched_by_normalized = False
        if purchase_price is None and product_id in purchase_prices_normalized:
            purchase_price = purchase_prices_normalized.get(product_id)
            matched_by_normalized = product_id not in purchase_prices
        if feed_price is None or purchase_price is None:
            labels[product.item_id] = UNKNOWN_MARGIN_LABEL
            stats["products_missing_purchase_price"] += 1
            stats["label_m_x"] += 1
            continue

        margin = feed_price - purchase_price - 70 - (feed_price * 0.05)
        label = _classify_margin(margin)
        labels[product.item_id] = label
        stats["products_with_purchase_price"] += 1
        if matched_by_normalized:
            stats["products_matched_by_normalized_code"] += 1
        if label == "m-s":
            stats["label_m_s"] += 1
        elif label == "m-m":
            stats["label_m_m"] += 1
        elif label == "m-l":
            stats["label_m_l"] += 1
        else:
            stats["label_m_xl"] += 1

    return labels, stats
