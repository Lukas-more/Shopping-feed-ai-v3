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
- Automaticky beh je nastaven na pevny cas `04:00 UTC`, tj. zhruba `05:00` v zime a `06:00` v lete v `Europe/Prague`.
- V GitHub repozitari je potreba nastavit secret `FEED_URL` s realnou URL vstupniho XML feedu.
- Secret `OPENAI_API_KEY` je volitelny. Kdyz nebude nastaveny, workflow i tak vygeneruje XML feed a auditni artifacty, jen bez AI optimalizace.
- AI cache z `data/cache.json` se v GitHub Actions obnovuje a uklada mezi behy, aby se stejne produkty znovu neposilaly do OpenAI.
- E-mail reporting po kazdem behu vyzaduje secrets `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` a volitelne `REPORT_EMAIL_FROM`.
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
- Hash produktu se pocita z `item_id`, `title`, vycisteneho `description_html`, `category_text` a normalizovanych variantnich parametru.
- Cache je v `data/cache.json`.
- Cache hit nastane jen kdyz sedi hash produktu i cache context (model + prompt/template nastaveni).
- V Actions logu a v `feed_run_report.json` uvidis `cache_hits`, `cache_misses`, `cache_miss_reasons`, `ai_selected_count`, `ai_calls`, `actual_input_tokens`, `actual_output_tokens`, `actual_cost_usd`, `cache_restored`, `cache_saved` a `cache_key`.
- `MAX_AI_PRODUCTS` je volitelny explicitni limit pres GitHub Actions variable nebo local env; bez explicitniho nastaveni se zadny tichy default nepouziva.
- Kdyz se cache neobnovi (`cache_restored=false`) a je aktivni OpenAI API klic, workflow zastavi AI cast fail-safe chovanim jeste pred ostrym AI during.
- Kdyz preflight ukaze necekane vysoky `ai_selected_count` nebo `cache_misses` a neni nastaveny explicitni `MAX_AI_PRODUCTS`, workflow aktivuje safety stop s jasnou chybou.
- Bez zmen produktu a bez zmen relevantni AI konfigurace by dalsi beh mel byt vyrazne levnejsi nez bootstrap prvni naplneni cache.
- Po dalsim runu zkontroluj v Actions logu kroky `Inspect cache after restore`, `Inspect cache after save` a v artifactu soubor `feed_run_report.json`.

## E-mail reporting
- Po kazdem behu workflow se odesila e-mail report na `lholer@seznam.cz`.
- Pro SMTP nastav v GitHub `Settings` -> `Secrets and variables` -> `Actions` tyto secrets: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`.
- Volitelne muzes nastavit `REPORT_EMAIL_FROM`, jinak se pouzije `SMTP_USERNAME`.
- Success report i failure report obsahuji maximum dostupnych provoznich metrik: status, cas reportu, products total, AI calls, cache hits, cache misses, `count_title_too_long`, token usage, USD cost, odkaz na `feed.xml` a odkaz na konkretni workflow run.
- Token usage a USD cost se berou z `feed_run_report.json`, ktery pipeline uklada do `data/output/`.
