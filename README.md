# Shopping Feed AI v2

Lokální aplikace pro převod a optimalizaci Heureka/Shoptet feedu do Google Merchant Center feedu.

## Co dělá
- vstup: Heureka/Shoptet XML feed (`SHOPITEM`)
- výstup: Google Merchant XML feed (`rss/channel/item` + `g:` namespace)
- zachová všechny důležité produktové informace pro GMC
- přes OpenAI optimalizuje jen vybraná pole:
  - `title`
  - `description`
  - `g:product_type`
  - `g:custom_label_3`
  - `g:custom_label_4`
- `g:custom_label_0` = marže (zatím fixně 40 %)
- `g:custom_label_1` = cenový bucket podle percentilů
- používá cache podle hash změn produktu
- ukazuje odhad ceny před během i skutečnou cenu po doběhu

## Instalace
```bash
pip install -r requirements.txt
```

## Spuštění UI
```bash
streamlit run app/streamlit_app.py
```

## CLI běh
```bash
python -m src.core.pipeline --settings config/settings.example.json --api-key TVUJ_KLIC
```

## Poznámky
- Feed pro GMC musí být po vygenerování dostupný na veřejné URL, pokud ho má Google Merchant Center stahovat automaticky.
- `ACCESSORY` z Heureka feedu nemá přímý standardní ekvivalent v GMC feedu a nepřenáší se.
- Pokud nepoužiješ OpenAI klíč, aplikace umí aspoň analyzovat feed a spočítat odhad produktů/ceny.
