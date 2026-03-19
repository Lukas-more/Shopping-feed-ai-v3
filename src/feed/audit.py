from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from src.core.models import Product


def build_audit_rows(products: list[Product], optimized_map: dict[str, dict]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for product in products:
        data = optimized_map.get(product.item_id, {})
        rows.append({
            "item_id": product.item_id,
            "original_title": product.title,
            "final_title": data.get("_final_title", product.title),
            "title_changed": data.get("_title_changed", False),
            "title_changed_by_postprocess": data.get("_title_changed_by_postprocess", False),
            "original_category": product.category_text,
            "final_product_type": data.get("_final_product_type", ""),
            "product_type_source": data.get("_product_type_source", ""),
            "product_type_reason": data.get("_product_type_reason", ""),
            "final_description": data.get("_final_description", ""),
            "description_changed": data.get("_description_changed", False),
            "description_source": data.get("_description_source", ""),
            "custom_label_0": data.get("_final_custom_label_0", ""),
            "custom_label_1": data.get("_final_custom_label_1", ""),
            "custom_label_3": data.get("_final_search_intent", ""),
            "custom_label_3_source": data.get("_search_intent_source", ""),
            "custom_label_3_reason": data.get("_search_intent_reason", ""),
            "custom_label_4": data.get("_final_segment", ""),
            "custom_label_4_source": data.get("_segment_source", ""),
            "custom_label_4_reason": data.get("_segment_reason", ""),
            "ai_used": data.get("_ai_used", False),
            "ai_success": data.get("_ai_success", False),
            "price": data.get("_final_price", product.price_vat),
            "availability": data.get("_availability", ""),
            "link": product.url,
            "params_summary": product.variant_text(),
        })
    return rows


def _fallback_output_path(output_path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return output_path.with_name(f"{output_path.stem}_{timestamp}{output_path.suffix}")


def write_audit_csv(rows: list[dict[str, object]], output_path: Path) -> tuple[Path, str | None]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "item_id",
        "original_title",
        "final_title",
        "title_changed",
        "title_changed_by_postprocess",
        "original_category",
        "final_product_type",
        "product_type_source",
        "product_type_reason",
        "final_description",
        "description_changed",
        "description_source",
        "custom_label_0",
        "custom_label_1",
        "custom_label_3",
        "custom_label_3_source",
        "custom_label_3_reason",
        "custom_label_4",
        "custom_label_4_source",
        "custom_label_4_reason",
        "ai_used",
        "ai_success",
        "price",
        "availability",
        "link",
        "params_summary",
    ]
    target_path = output_path
    warning: str | None = None
    try:
        with target_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter=";")
            writer.writeheader()
            writer.writerows(rows)
    except PermissionError:
        target_path = _fallback_output_path(output_path)
        warning = f"Audit CSV byl zamceny, zapis pouzit do nahradniho souboru {target_path.name}."
        with target_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter=";")
            writer.writeheader()
            writer.writerows(rows)
    return target_path, warning
