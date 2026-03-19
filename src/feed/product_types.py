from __future__ import annotations

import re

from src.utils.xml_helpers import clean_html_text


_MARKETPLACE_PREFIXES = {
    "heureka.cz",
}

_GENERIC_BRANCH_GUARDS = [
    {
        "prefix": "Dum a kuchyne > Kuchynske pomucky > Krajeni a priprava",
        "keywords": ["prken", "krajec", "kuchyn", "nuz", "krajeni"],
    },
    {
        "prefix": "Hobby a zahrada > Zahrada > Zahradni rukavice",
        "keywords": ["rukavic", "zahradni rukavic"],
    },
]

_CATEGORY_CONFLICT_RULES = [
    {
        "prefix": "Dum a uklid > Uklidove pomucky > Cistici kartace a houbicky",
        "forbidden": ["letadlo", "hracka", "detsk", "panenka", "puzzle", "stavebnice", "projektor", "nocni oblohy"],
    },
    {
        "prefix": "Sport a outdoor > Outdoor > Celovky a svitilny",
        "forbidden": ["letadlo", "hracka", "detsk", "panenka", "puzzle", "stavebnice", "sprcha", "hlavice", "koupelna", "koberecek", "zrcadlo", "baterie", "kabel", "nabijecka", "sluchatka", "dongle"],
    },
    {
        "prefix": "Kraska a pece o telo > Kosmeticke pomucky",
        "forbidden": ["ponozky", "podprsenka", "pyzamo", "leginy"],
    },
    {
        "prefix": "Dum a bydleni > Bytovy textil",
        "forbidden": ["ortoped", "zdravotni pomuck", "bandaz"],
    },
    {
        "prefix": "Auto-moto > Autodoplnky > Prakticke doplnky",
        "forbidden": ["sprcha", "hlavice", "koupelna", "koberecek", "zrcadlo"],
    },
    {
        "prefix": "Hracky a zabava > Hracky > Darkove a sberatelske zbozi",
        "forbidden": ["organizer do auta", "drzak do auta", "box mezi sedacky"],
    },
]

_KEYWORD_RULES = [
    {
        "patterns": [r"\bcistici kartac", r"\bkartac", r"\bhoubic", r"\bhouba", r"\buklid"],
        "required_terms": ["kartac", "houb", "uklid", "cistic"],
        "product_type": "Dum a uklid > Uklidove pomucky > Cistici kartace a houbicky",
    },
    {
        "patterns": [r"\baku\b", r"\bfukar", r"\bpilk", r"\bnuzk", r"\bkrovinorez"],
        "required_terms": ["aku", "fukar", "pilk", "nuzk", "krovinorez"],
        "product_type": "Hobby a zahrada > Zahradni technika > AKU naradi",
    },
    {
        "patterns": [r"\bauto\b", r"\bkryt", r"\bpotah", r"\bdrzak do auta", r"\badapter do auta"],
        "required_terms": ["auto", "kryt", "potah", "drzak", "adapter"],
        "product_type": "Auto-moto > Autodoplnky > Prakticke doplnky",
    },
    {
        "patterns": [r"\bkosmet", r"\bmake-up", r"\bstetec", r"\bpincet", r"\bmanik", r"\bpedik"],
        "required_terms": ["kosmet", "stetec", "pincet", "manik", "pedik"],
        "product_type": "Kraska a pece o telo > Kosmeticke pomucky",
    },
    {
        "patterns": [r"\bbandaz", r"\bortez", r"\bkolen", r"\bortoped", r"\bzdravotn", r"\bpolstar"],
        "required_terms": ["bandaz", "ortez", "kolen", "ortoped", "zdravotn", "polstar"],
        "product_type": "Zdravi > Ortopedicke pomucky > Bandaze a zdravotni pomucky",
    },
    {
        "patterns": [r"\bcelovk", r"\bsvitiln", r"\boutdoor svetl", r"\bosvetlen"],
        "required_terms": ["celovk", "svitiln", "osvetlen", "outdoor"],
        "product_type": "Sport a outdoor > Outdoor > Celovky a svitilny",
    },
    {
        "patterns": [r"\bhrack", r"\bstavebnic", r"\bpuzzle", r"\bsberat", r"\bdark"],
        "required_terms": ["hrack", "stavebnic", "puzzle", "sberat", "dark"],
        "product_type": "Hracky a zabava > Hracky > Darkove a sberatelske zbozi",
    },
    {
        "patterns": [r"\btextil", r"\bpolstar", r"\bdeka", r"\bpovlak", r"\bprostirad", r"\bzaves"],
        "required_terms": ["textil", "deka", "povlak", "prostirad", "zaves", "polstar"],
        "product_type": "Dum a bydleni > Bytovy textil",
    },
    {
        "patterns": [r"\bspaci pyt", r"\bkempovac"],
        "required_terms": ["spaci pyt", "kemp"],
        "product_type": "Sport a outdoor > Kemping > Spaci pytle",
    },
    {
        "patterns": [r"\bherni konzol", r"\bgame box", r"\bretro konzol"],
        "required_terms": ["konzol", "game box", "retro"],
        "product_type": "Elektronika > Herni konzole > Prenosne konzole",
    },
]


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


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip()


def _normalize_path(value: str) -> str:
    if not value:
        return ""
    normalized = value.replace("/", " > ").replace("|", " > ")
    normalized = re.sub(r"\s*>\s*", " > ", normalized)
    parts = [_normalize_whitespace(part) for part in normalized.split(">")]
    parts = [part for part in parts if part and _normalize_ascii(part) not in _MARKETPLACE_PREFIXES]
    return " > ".join(parts)


def _trim_levels(value: str, min_levels: int = 2, max_levels: int = 4) -> str:
    parts = [part.strip() for part in value.split(">") if part.strip()]
    if len(parts) < min_levels:
        return ""
    return " > ".join(parts[:max_levels])


def clean_original_category(original_category: str) -> str:
    return _trim_levels(_normalize_path(original_category))


def _build_haystack(title: str, description: str, params: dict[str, str] | None = None) -> str:
    params_text = ""
    if params:
        params_text = " ".join(f"{key} {value}" for key, value in params.items())
    return _normalize_ascii(f"{title} {description} {params_text}")


def _match_rule(title: str, description: str, params: dict[str, str] | None = None) -> dict | None:
    haystack = _build_haystack(title, description, params)
    for rule in _KEYWORD_RULES:
        if any(re.search(pattern, haystack) for pattern in rule["patterns"]):
            return rule
    return None


def _is_marketplace_like(ai_product_type: str) -> bool:
    candidate = ai_product_type or ""
    if "heureka.cz" in candidate.lower():
        return True
    return candidate.count("|") >= 3


def _is_guard_branch_mismatch(candidate: str, haystack: str) -> bool:
    candidate_ascii = _normalize_ascii(candidate)
    for guard in _GENERIC_BRANCH_GUARDS:
        if candidate_ascii.startswith(_normalize_ascii(guard["prefix"])):
            return not any(keyword in haystack for keyword in guard["keywords"])
    return False


def _has_conflict_keywords(candidate: str, haystack: str) -> bool:
    candidate_ascii = _normalize_ascii(candidate)
    for rule in _CATEGORY_CONFLICT_RULES:
        if candidate_ascii.startswith(_normalize_ascii(rule["prefix"])):
            return any(keyword in haystack for keyword in rule["forbidden"])
    return False


def _soften_branch(candidate: str) -> str:
    parts = [part.strip() for part in candidate.split(">") if part.strip()]
    if len(parts) >= 2:
        return " > ".join(parts[:2])
    return candidate


def _validate_ai_product_type(
    ai_product_type: str,
    title: str,
    description: str,
    params: dict[str, str] | None = None,
) -> tuple[str, str]:
    if not ai_product_type or not ai_product_type.strip():
        return "", ""
    if _is_marketplace_like(ai_product_type):
        return "", "marketplace_like_ai"
    normalized = _trim_levels(_normalize_path(ai_product_type))
    if not normalized:
        return "", ""
    haystack = _build_haystack(title, description, params)
    rule = _match_rule(title, description, params)
    if rule and not any(term in _normalize_ascii(normalized) for term in rule["required_terms"]):
        return "", "rule_conflict"
    if _is_guard_branch_mismatch(normalized, haystack):
        return "", "guard_branch_conflict"
    if _has_conflict_keywords(normalized, haystack):
        return "", "conflict_keywords"
    return normalized, ""


def resolve_product_type_with_source(
    ai_product_type: str,
    original_category: str,
    title: str,
    description: str,
    params: dict[str, str] | None = None,
) -> tuple[str, str, str]:
    clean_description = clean_html_text(description or "", max_len=2000)
    valid_ai, ai_reason = _validate_ai_product_type(ai_product_type, title, clean_description, params)
    if valid_ai:
        return valid_ai, "kept_ai_result", "validated_ai_product_type"

    rule = _match_rule(title, clean_description, params)
    if rule:
        source = "rule_override"
        if ai_reason in {"guard_branch_conflict", "conflict_keywords"}:
            source = "blacklist_correction"
        if not _has_conflict_keywords(rule["product_type"], _build_haystack(title, clean_description, params)):
            return rule["product_type"], source, rule["product_type"]

    fallback_category = clean_original_category(original_category)
    haystack = _build_haystack(title, clean_description, params)
    if fallback_category and (_is_guard_branch_mismatch(fallback_category, haystack) or _has_conflict_keywords(fallback_category, haystack)):
        fallback_category = _soften_branch(fallback_category)
        reason = "rejected_conflict_category_fallback" if _has_conflict_keywords(fallback_category, haystack) else "rejected_generic_bad_fallback"
        return fallback_category, "blacklist_correction", reason

    return fallback_category, "fallback_from_original_category", "fallback_to_safe_original_category"


def resolve_product_type(
    ai_product_type: str,
    original_category: str,
    title: str,
    description: str,
    params: dict[str, str] | None = None,
) -> str:
    resolved, _source, _reason = resolve_product_type_with_source(
        ai_product_type=ai_product_type,
        original_category=original_category,
        title=title,
        description=description,
        params=params,
    )
    return resolved


def _run_sanity_assertions() -> None:
    assert "Cistici kartace" not in resolve_product_type("", "", "Projektor nocni oblohy", "Dekorativni projektor hvezdne oblohy")
    assert "Celovky" not in resolve_product_type("", "", "Detske letadlo", "Hracka pro deti")
    assert "Celovky" not in resolve_product_type("", "", "Sprchova hlavice", "Hlavice do koupelny")
    assert "Hracky" not in resolve_product_type("", "", "Organizer do auta", "Box mezi sedacky do auta")
    assert "Kosmeticke pomucky" not in resolve_product_type("", "", "Ponozky", "Damske ponozky")
    assert "Celovky" not in resolve_product_type("", "", "USB kabel a baterie", "Kabel a baterie")


_run_sanity_assertions()
