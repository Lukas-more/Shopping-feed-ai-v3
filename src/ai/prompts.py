import json
from pathlib import Path

from src.core.models import Product
from src.utils.xml_helpers import clean_html_text


def load_templates(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _fill_template(template_text: str, values: dict[str, str]) -> str:
    filled = template_text
    for key, value in values.items():
        filled = filled.replace("{" + key + "}", value)
    return filled


def build_prompt(template_text: str, product: Product) -> str:
    clean_desc = clean_html_text(product.description_html, max_len=900)
    variant_text = product.variant_text()
    formatted_template = _fill_template(template_text, {
        "original_title": product.title or "",
        "category": product.category_text or "",
        "description": clean_desc,
        "params": variant_text,
        "delivery_date": product.delivery_date or "",
    })
    return (
        f"{formatted_template}\n\n"
        f"Produkt:\n"
        f"Nazev: {product.title}\n"
        f"Kategorie: {product.category_text}\n"
        f"Cena: {product.price_vat}\n"
        f"Varianty: {variant_text}\n"
        f"Popis: {clean_desc}\n"
    )
