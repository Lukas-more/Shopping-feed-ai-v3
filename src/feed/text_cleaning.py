from __future__ import annotations

import html
import re


_TITLE_BLACKLIST_PATTERNS = [
    r"\bnejleps[iiíý]\b",
    r"\bskv[eě]l[yý]\b",
    r"\btop\b",
    r"\bakce\b",
    r"\bsleva\b",
    r"\bsuper\b",
    r"\brevolu[cč]n[ií]\b",
    r"\bbezpe[cč]n[aá]\s+hra[cč]ka\s+pro\s+d[eě]ti\b",
    r"\bpro\s+vodn[ií]\s+radov[aá]nky\b",
]

_TITLE_SUFFIX_NOISE = [
    r"\bpro\s+dom[aá]cnost\b$",
    r"\bpro zabavu\b$",
    r"\bpro\s+voln[yý]\s+[cč]as\b$",
]

_DESCRIPTION_NOISE_PATTERNS = [
    r"akce plati do vyprodani zasob",
    r"skladem poslednich par kusu",
    r"doruceni do 24 hodin",
    r"\d+\+ spokojenych zakazniku",
    r"objednejte ihned",
    r"nakupte hned",
    r"detailni popis produktu",
    r"ilustracni video",
    r"\bvideo\b",
]

_VAGUE_DESCRIPTION_PATTERNS = [
    r"\bidealni pomocnik\b",
    r"\bskvely pomocnik\b",
    r"\bkvalitni provedeni\b",
    r"\bpro kazdodenni pouziti\b",
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


def _clean_edges(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"[\s,;:>\-|]+$", "", value)
    value = re.sub(r"^[\s,;:>\-|]+", "", value)
    return value.strip()


def _truncate_clean(value: str, max_len: int) -> str:
    if len(value) <= max_len:
        return value
    truncated = value[: max_len + 1]
    if " " in truncated:
        truncated = truncated.rsplit(" ", 1)[0]
    return _clean_edges(truncated)


def normalize_title(title: str) -> tuple[str, bool]:
    original = html.unescape(title or "").strip()
    value = original
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"\s*(\||•|>>)+\s*", " ", value)
    value = re.sub(r"\b(\d+)\s*ks\b", r"\1 ks", value, flags=re.I)
    value = re.sub(r"\b(\d+)x(?=\s*(ks|kus|baleni|set|sada)\b)", r"\1 ks", value, flags=re.I)
    value = re.sub(r"\bUSB\s*-\s*C\b", "USB-C", value, flags=re.I)
    value = re.sub(r"\bPush\s*-\s*up\b", "Push-up", value, flags=re.I)
    value = re.sub(r"\b([A-Z]{1,4})\s*-\s*([A-Z0-9]{1,4})\b", r"\1-\2", value)
    value = re.sub(r"\b([A-Z]{1,3}\d*)\s*-\s*(\d{2,4})\b", r"\1-\2", value)
    value = re.sub(r"\b(\w+)\s+-\s+(\w+)\b", r"\1 - \2", value)

    for pattern in _TITLE_BLACKLIST_PATTERNS:
        value = re.sub(pattern, " ", value, flags=re.I)
    for pattern in _TITLE_SUFFIX_NOISE:
        value = re.sub(pattern, " ", value, flags=re.I)

    value = re.sub(r"\b(\w+)\s+\1\b", r"\1", value, flags=re.I)
    value = _clean_edges(value)
    value = _truncate_clean(value, max_len=70)
    return value, value != original


def _remove_html_noise(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<(script|style|meta).*?>.*?</\1>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<iframe.*?</iframe>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<video.*?</video>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<img[^>]*>", " ", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"http\S+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _remove_noise_phrases(value: str) -> str:
    cleaned = value
    for pattern in _DESCRIPTION_NOISE_PATTERNS:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _unique_sentences(value: str) -> list[str]:
    candidates = re.split(r"(?<=[.!?])\s+", value)
    result: list[str] = []
    seen: set[str] = set()
    for sentence in candidates:
        clean_sentence = _clean_edges(sentence)
        if len(clean_sentence) < 20:
            continue
        fingerprint = _normalize_ascii(clean_sentence)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        result.append(clean_sentence)
    return result


def build_fallback_description(raw_html_or_text: str) -> str:
    cleaned = _remove_html_noise(raw_html_or_text)
    cleaned = _remove_noise_phrases(cleaned)
    sentences = _unique_sentences(cleaned)

    if not sentences:
        return _truncate_clean(cleaned, max_len=400)

    selected: list[str] = []
    total_length = 0
    for sentence in sentences[:4]:
        projected = total_length + len(sentence) + (1 if selected else 0)
        if projected > 400:
            break
        selected.append(sentence)
        total_length = projected
        if total_length >= 160 and len(selected) >= 2:
            break

    result = " ".join(selected) if selected else cleaned
    return _truncate_clean(result, max_len=400)


def _build_attribute_description(title: str, category: str, params: dict[str, str] | None = None) -> str:
    category_hint = category.split("|")[-1].strip() if "|" in category else category.split(">")[-1].strip()
    params_text = ""
    if params:
        interesting = [f"{key}: {value}" for key, value in params.items()][:3]
        if interesting:
            params_text = " Vybrane parametry: " + ", ".join(interesting) + "."
    base = f"{title} je produkt z kategorie {category_hint}."
    return _truncate_clean(base + params_text, max_len=320)


def _is_vague_description(text: str, title: str) -> bool:
    normalized = _normalize_ascii(text)
    if len(normalized) < 80:
        return True
    if sum(1 for pattern in _VAGUE_DESCRIPTION_PATTERNS if re.search(pattern, normalized)) >= 2:
        return True
    title_tokens = [token for token in re.findall(r"\w+", _normalize_ascii(title)) if len(token) > 3][:4]
    if title_tokens and not any(token in normalized for token in title_tokens):
        return True
    if not any(phrase in normalized for phrase in [" je ", " slouzi ", " urcen ", " pomaha ", " umoznuje "]):
        return True
    return False


def finalize_description(
    ai_description: str,
    raw_html_or_text: str,
    title: str,
    category: str,
    params: dict[str, str] | None = None,
) -> tuple[str, str]:
    fallback = build_fallback_description(raw_html_or_text)
    if ai_description and ai_description.strip():
        cleaned_ai = _truncate_clean(_clean_edges(_remove_html_noise(ai_description)), max_len=400)
        if cleaned_ai and not _is_vague_description(cleaned_ai, title):
            return cleaned_ai, "kept_ai_result"
    if fallback and not _is_vague_description(fallback, title):
        return fallback, "fallback_from_original_description"
    return _build_attribute_description(title, category, params), "fallback_from_attributes"
