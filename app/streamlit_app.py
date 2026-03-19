from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st
from requests import RequestException

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.ai.prompts import load_templates
from src.core.pipeline import load_settings, run_pipeline
from src.utils.secure_storage import (
    delete_api_key,
    has_saved_api_key,
    load_api_key,
    save_api_key,
)


def _show_friendly_error(exc: Exception) -> None:
    message = str(exc)
    lower_message = message.lower()

    if isinstance(exc, PermissionError) or "permission denied" in lower_message:
        st.error("Nepodarilo se zapsat vystupni soubor. Nejpravdepodobneji je otevreny v Excelu nebo jinem programu.")
        st.info("Zavri otevrene XML, CSV nebo JSON soubory v data/output a spust beh znovu.")
        return

    if isinstance(exc, RuntimeError) and "nepodarilo se stahnout vstupni feed" in lower_message:
        st.error(message)
        st.info("Zkontroluj feed URL, internetove pripojeni a pripadne dostupnost exportu na strane e-shopu.")
        return

    if isinstance(exc, RequestException):
        st.error("Nepodarilo se stahnout vstupni feed.")
        st.info("Zkontroluj feed URL a internetove pripojeni.")
        return

    st.error("Beh skoncil chybou.")
    st.exception(exc)


st.set_page_config(page_title="Shopping Feed AI v2", layout="wide")
st.title("Shopping Feed AI v2")
st.caption("Heureka/Shoptet feed -> Google Merchant feed")
st.info(
    "Odhad i optimalizace pouzivaji cache. Do AI by mely jit jen zmenene a aktivni produkty, "
    "ktere nejsou shodne s ulozenym hashem v data/cache.json."
)

settings_path = ROOT / "config" / "settings.example.json"
settings = load_settings(str(settings_path))
templates = load_templates(ROOT / "config" / "prompt_templates.json")
saved_api_key_exists = has_saved_api_key()

if "api_key_input" not in st.session_state:
    st.session_state.api_key_input = ""

col1, col2 = st.columns(2)
with col1:
    feed_url = st.text_input("Feed URL", value=settings["feed_url"])
    api_key = st.text_input("OpenAI API key", type="password", key="api_key_input")
    use_saved_key = st.checkbox("Pouzit bezpecne ulozeny API klic", value=saved_api_key_exists)
    key_col1, key_col2 = st.columns(2)
    with key_col1:
        if st.button("Ulozit API klic bezpecne", use_container_width=True):
            if st.session_state.api_key_input.strip():
                save_api_key(st.session_state.api_key_input.strip())
                st.success("API klic byl ulozen pres DPAPI.")
                saved_api_key_exists = True
            else:
                st.warning("Nejdriv zadej API klic.")
    with key_col2:
        if st.button("Smazat ulozeny klic", use_container_width=True):
            delete_api_key()
            st.success("Ulozeny API klic byl smazan.")
            saved_api_key_exists = False
    model = st.selectbox("Model", ["gpt-4o-mini", "gpt-4.1-mini", "gpt-4.1"], index=0)
    margin = st.number_input(
        "Vychozi marze %",
        min_value=0,
        max_value=100,
        value=int(settings["default_margin_percent"]),
    )
    active_max = st.number_input(
        "Max DELIVERY_DATE pro AI",
        min_value=0,
        max_value=30,
        value=int(settings["delivery_date_active_max"]),
    )
with col2:
    prompt_template = st.selectbox("Prompt sablona", list(templates.keys()), index=0)
    custom_prompt = st.text_area("Vlastni prompt (volitelne)", value="", height=180)
    margin_csv_path = st.text_input("CSV marzi (volitelne)", value="")

run1, run2 = st.columns(2)
with run1:
    dry_run = st.button("Spocitat odhad")
with run2:
    execute = st.button("Spustit optimalizaci")

runtime_settings = settings | {
    "feed_url": feed_url,
    "model": model,
    "default_margin_percent": margin,
    "delivery_date_active_max": active_max,
    "prompt_template": prompt_template,
    "custom_prompt": custom_prompt,
    "margin_csv_path": margin_csv_path,
}

effective_api_key = api_key.strip()
if not effective_api_key and use_saved_key and saved_api_key_exists:
    effective_api_key = load_api_key()

if dry_run or execute:
    if execute and not effective_api_key:
        st.error("Pro spusteni optimalizace chybi OpenAI API klic.")
        st.info("Zadej API klic nebo zapni volbu pro bezpecne ulozeny API klic.")
        st.stop()

    try:
        result = run_pipeline(runtime_settings, api_key=effective_api_key or None, dry_run=not execute)
        st.subheader("Vysledek")
        st.json(result)
        for warning in result.get("warnings", []):
            st.warning(warning)
        if use_saved_key and saved_api_key_exists and not api_key.strip():
            st.caption("Pro tento beh byl pouzit API klic ulozeny bezpecne pres DPAPI.")
        if execute:
            output = Path(result["output_path"])
            if output.exists():
                st.success(f"Feed vytvoren: {output}")
                st.download_button(
                    "Stahnout XML feed",
                    data=output.read_bytes(),
                    file_name=output.name,
                    mime="application/xml",
                )
    except Exception as e:
        _show_friendly_error(e)
