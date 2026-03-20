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
## GitHub Actions
- Workflow je v `.github/workflows/feed.yml`.
- Spousti se rucne pres `workflow_dispatch` a take 1x denne.
- Automaticky beh je nastaven na 05:30 `Europe/Prague` a je osetreny proti letnimu/zimnimu casu (DST).
- V GitHub repozitari je potreba nastavit secret `FEED_URL` s realnou URL vstupniho XML feedu.
- Secret `OPENAI_API_KEY` je volitelny. Kdyz nebude nastaveny, workflow i tak vygeneruje XML feed a auditni artifacty, jen bez AI optimalizace.
- AI cache z `data/cache.json` se v GitHub Actions obnovuje a uklada mezi behy, aby se stejne produkty znovu neposilaly do OpenAI.
- Rucni spusteni: GitHub `Actions` -> `Generate Feed` -> `Run workflow`.

## GitHub Pages
- Workflow po vygenerovani feedu publikuje `data/output/optimized_feed.xml` na GitHub Pages jako stabilni `feed.xml`.
- Ocekavana URL pro tento repozitar je `https://lukas-more.github.io/Shopping-feed-ai-v3/feed.xml`.
- Pokud Pages jeste nebezi, v GitHubu otevri `Settings` -> `Pages` a jako source nastav `GitHub Actions`.
- Po uspesnem behu workflow najdes verejnou URL i v sekci `Deploy to GitHub Pages` nebo v `Settings` -> `Pages`.
- Rucni spusteni workflow zustava: `Actions` -> `Generate Feed` -> `Run workflow`.

## Prvni spusteni checklist
- V GitHub repozitari otevri `Settings` -> `Secrets and variables` -> `Actions` a zaloz secret `FEED_URL`.
- Jako hodnotu `FEED_URL` nastav: `https://www.plaza.cz/heureka/export/products.xml?hash=X4SOE1liV0PnOQmeqEid2jX`
- Otevri `Settings` -> `Pages` a jako source nastav `GitHub Actions`.
- Otevri `Actions` -> `Generate Feed` -> `Run workflow`.
- Po uspesnem dobehu over verejnou URL `https://lukas-more.github.io/Shopping-feed-ai-v3/feed.xml`.

## AI cache
- Hash produktu se pocita z `item_id`, `title`, vycisteneho `description_html`, `category_text` a `variant_text`.
- Cache je v `data/cache.json`.
- Cache hit nastane jen kdyz sedi hash produktu i cache context (model + prompt/template nastaveni).
- V Actions logu a v JSON vystupu uvidis `cache_hits`, `cache_misses`, `ai_candidates`, `ai_calls`, `ai_skipped_missing_key` a `ai_skipped_due_limit`.
- Ochranny limit lze nastavit pres GitHub Actions environment variable nebo local env `MAX_AI_PRODUCTS`.
- Bez zmen produktu a bez zmen relevantni AI konfigurace by dalsi beh mel byt vyrazne levnejsi nez bootstrap prvni naplneni cache.
