from __future__ import annotations

from collections import Counter

from src.core.models import Product


def build_qa_report(products: list[Product], optimized_map: dict[str, dict], run_stats: dict[str, object]) -> dict[str, object]:
    title_too_long = 0
    title_empty = 0
    description_empty = 0
    description_too_short = 0
    product_type_sources = Counter()
    intent_sources = Counter()
    segment_sources = Counter()
    custom_label_3 = Counter()
    custom_label_4 = Counter()
    custom_label_0 = Counter()

    for product in products:
        data = optimized_map.get(product.item_id, {})
        final_title = (data.get("_final_title") or "").strip()
        final_description = (data.get("_final_description") or "").strip()
        product_type_source = data.get("_product_type_source", "fallback_from_category")
        intent_source = data.get("_search_intent_source", "fallback_default")
        segment_source = data.get("_segment_source", "fallback_default")
        final_intent = data.get("_final_search_intent", "")
        final_segment = data.get("_final_segment", "")
        final_margin_label = data.get("_final_custom_label_0", "")

        if not final_title:
            title_empty += 1
        if len(final_title) > 70:
            title_too_long += 1
        if not final_description:
            description_empty += 1
        if final_description and len(final_description) < 120:
            description_too_short += 1

        product_type_sources[product_type_source] += 1
        intent_sources[intent_source] += 1
        segment_sources[segment_source] += 1
        if final_intent:
            custom_label_3[final_intent] += 1
        if final_segment:
            custom_label_4[final_segment] += 1
        if final_margin_label:
            custom_label_0[final_margin_label] += 1

    return {
        "products_total": run_stats["products_total"],
        "ai_candidates": run_stats["ai_candidates"],
        "ai_calls": run_stats["ai_calls"],
        "ai_errors": run_stats["ai_errors"],
        "count_title_too_long": title_too_long,
        "count_title_empty": title_empty,
        "count_description_empty": description_empty,
        "count_description_too_short": description_too_short,
        "count_product_type_from_ai": product_type_sources.get("ai", 0),
        "count_product_type_from_fallback": run_stats["products_total"] - product_type_sources.get("ai", 0),
        "count_intent_from_ai": intent_sources.get("ai", 0),
        "count_intent_from_fallback": run_stats["products_total"] - intent_sources.get("ai", 0),
        "count_segment_from_ai": segment_sources.get("ai", 0),
        "count_segment_from_fallback": run_stats["products_total"] - segment_sources.get("ai", 0),
        "count_custom_label_0_m_x": run_stats["count_custom_label_0_m_x"],
        "count_custom_label_0_m_s": run_stats["count_custom_label_0_m_s"],
        "count_custom_label_0_m_m": run_stats["count_custom_label_0_m_m"],
        "count_custom_label_0_m_l": run_stats["count_custom_label_0_m_l"],
        "count_custom_label_0_m_xl": run_stats["count_custom_label_0_m_xl"],
        "purchase_csv_present": run_stats["purchase_csv_present"],
        "purchase_csv_bytes": run_stats["purchase_csv_bytes"],
        "purchase_csv_looks_like_html": run_stats["purchase_csv_looks_like_html"],
        "purchase_csv_encoding": run_stats["purchase_csv_encoding"],
        "purchase_csv_delimiter": run_stats["purchase_csv_delimiter"],
        "purchase_csv_header_preview": run_stats["purchase_csv_header_preview"],
        "purchase_csv_row_count": run_stats["purchase_csv_row_count"],
        "purchase_csv_rows_loaded": run_stats["purchase_csv_rows_loaded"],
        "purchase_csv_rows_with_purchase_price": run_stats["purchase_csv_rows_with_purchase_price"],
        "purchase_csv_code_samples": run_stats["purchase_csv_code_samples"],
        "feed_id_samples": run_stats["feed_id_samples"],
        "purchase_csv_match_count_exact": run_stats["purchase_csv_match_count_exact"],
        "purchase_csv_match_count_normalized": run_stats["purchase_csv_match_count_normalized"],
        "products_matched_by_normalized_code": run_stats["products_matched_by_normalized_code"],
        "products_with_purchase_price": run_stats["products_with_purchase_price"],
        "product_type_source_breakdown": dict(product_type_sources),
        "custom_label_0_breakdown": dict(custom_label_0),
        "custom_label_3_breakdown": dict(custom_label_3),
        "custom_label_4_breakdown": dict(custom_label_4),
        "intent_source_breakdown": dict(intent_sources),
        "segment_source_breakdown": dict(segment_sources),
    }
