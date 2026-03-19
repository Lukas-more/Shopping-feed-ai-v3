from __future__ import annotations

import re

from src.utils.xml_helpers import clean_html_text


SEARCH_INTENT_VALUES = {"commercial", "comparison", "accessory", "replacement", "premium", "budget"}
SEGMENT_VALUES = {"core_product", "upsell", "addon", "seasonal", "gift"}


def _normalize_ascii(value: str) -> str:
    replacements = {
        "á": "a",
        "č": "c",
        "ď": "d",
        "é": "e",
        "ě": "e",
        "í": "i",
        "ň": "n",
        "ó": "o",
        "ř": "r",
        "š": "s",
        "ť": "t",
        "ú": "u",
        "ů": "u",
        "ý": "y",
        "ž": "z",
    }
    normalized = (value or "").lower()
    for src, dst in replacements.items():
        normalized = normalized.replace(src, dst)
    return normalized


def _build_haystack(title: str, description: str, category: str, params: dict[str, str] | None = None) -> str:
    params_text = ""
    if params:
        params_text = " ".join(f"{key} {value}" for key, value in params.items())
    clean_description = clean_html_text(description or "", max_len=1500)
    return _normalize_ascii(f"{title} {clean_description} {category} {params_text}")


def _matches_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def _is_multipack(text: str) -> bool:
    return _matches_any(text, [r"\bset\b", r"\bsada\b", r"\bpack\b", r"\bmultipack\b", r"\b\d+\s*x\b", r"\b\d+\s*(ks|kusu?)\b"])


def _has_variant_signal(text: str) -> bool:
    return _matches_any(text, [r"\b\d+\s*(cm|mm|m|ml|l|gb|mah|w|v)\b", r"\bvelikost\b", r"\bobjem\b", r"\bdelka\b", r"\bdosvit\b", r"\bkapacita\b", r"\bvykon\b", r"\bbarva\b"])


def _rule_search_intent(text: str) -> str:
    if _matches_any(text, [r"\bbateri", r"\btermopapir", r"\bfiltr", r"\bnahradn", r"\bvlozk", r"\bcistici kamen", r"\bhoubic", r"\bhouba", r"\bcistici kartac"]):
        return "replacement"

    if _matches_any(text, [r"\badapter", r"\bdrzak", r"\bobal", r"\bpouzdro", r"\bbrasna", r"\bpodlozk", r"\bprislusenstv", r"\bkryt na auto", r"\bpotah", r"\bspořic vody", r"\bsporic vody"]):
        return "accessory"

    if _matches_any(text, [r"\baku\b", r"\bfukar", r"\bpilk", r"\bnuzk", r"\bkrovinorez", r"\bklimatizac", r"\bzastrihovac", r"\bcelovk", r"\bsvitiln", r"\bmasazni pistol", r"\bkonzol", r"\bpristroj"]) or _has_variant_signal(text):
        return "comparison"

    if _matches_any(text, [r"\bxl\b", r"\bmax\b", r"\bplus\b", r"\bdeluxe\b", r"\bpremium\b"]):
        return "premium"

    if _matches_any(text, [r"\bmini\b", r"\bzakladni\b", r"\bjednoduch", r"\bnouzov"]):
        return "budget"

    if _matches_any(text, [r"\bdarek", r"\bjednorozec", r"\bpuzzle", r"\bhrack", r"\bnovelty\b"]):
        return "commercial"

    return ""


def _rule_segment(text: str, search_intent: str) -> str:
    if _matches_any(text, [r"\bvanoce", r"\badvent", r"\bletni\b", r"\bzimni\b", r"\bbazen", r"\blehatko", r"\bplaz", r"\bzahrad", r"\bkemp"]):
        return "seasonal"

    if _matches_any(text, [r"\bdarek", r"\bdarkov", r"\bjednorozec", r"\bpuzzle", r"\bpro deti", r"\bhrack", r"\bsberat", r"\bnovelty\b"]):
        return "gift"

    if search_intent in {"accessory", "replacement"}:
        return "addon"

    if _is_multipack(text) or _matches_any(text, [r"\bxl\b", r"\bmax\b", r"\bplus\b", r"\bvelky\b"]):
        return "upsell"

    return ""


def _validate_enum(ai_value: str, allowed: set[str]) -> str:
    normalized = (ai_value or "").strip().lower()
    return normalized if normalized in allowed else ""


def resolve_search_intent_with_source(
    ai_value: str,
    title: str,
    description: str,
    category: str,
    params: dict[str, str] | None = None,
) -> tuple[str, str, str]:
    haystack = _build_haystack(title, description, category, params)
    rule_value = _rule_search_intent(haystack)
    ai_normalized = _validate_enum(ai_value, SEARCH_INTENT_VALUES)

    if rule_value and ai_normalized and ai_normalized != rule_value:
        return rule_value, "rule_override", "search_intent_rule_override"
    if ai_normalized:
        return ai_normalized, "kept_ai_result", "validated_ai_enum"
    if rule_value:
        return rule_value, "rule_override", "search_intent_rule_match"
    return "commercial", "fallback_default", "safe_default_commercial"


def resolve_segment_with_source(
    ai_value: str,
    title: str,
    description: str,
    category: str,
    params: dict[str, str] | None = None,
) -> tuple[str, str, str]:
    haystack = _build_haystack(title, description, category, params)
    inferred_intent = _rule_search_intent(haystack)
    rule_value = _rule_segment(haystack, inferred_intent)
    ai_normalized = _validate_enum(ai_value, SEGMENT_VALUES)

    if rule_value and ai_normalized and ai_normalized != rule_value:
        return rule_value, "rule_override", "segment_rule_override"
    if ai_normalized:
        return ai_normalized, "kept_ai_result", "validated_ai_enum"
    if rule_value:
        return rule_value, "rule_override", "segment_rule_match"
    return "core_product", "fallback_default", "safe_default_core_product"


def resolve_search_intent(
    ai_value: str,
    title: str,
    description: str,
    category: str,
    params: dict[str, str] | None = None,
) -> str:
    value, _source, _reason = resolve_search_intent_with_source(ai_value, title, description, category, params)
    return value


def resolve_segment(
    ai_value: str,
    title: str,
    description: str,
    category: str,
    params: dict[str, str] | None = None,
) -> str:
    value, _source, _reason = resolve_segment_with_source(ai_value, title, description, category, params)
    return value
