import re
from html import unescape
from lxml import etree as ET


def inner_xml(elem: ET._Element | None) -> str:
    if elem is None:
        return ""
    return "".join(ET.tostring(child, encoding="unicode") for child in elem.iterchildren()) or (elem.text or "")


def clean_html_text(text: str, max_len: int = 1200) -> str:
    text = unescape(text or "")
    text = re.sub(r"<iframe.*?</iframe>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"http\S+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len]


def parse_cz_price(price_text: str) -> float:
    if not price_text:
        return 0.0
    cleaned = re.sub(r"[^\d,.-]", "", price_text).replace(" ", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0
