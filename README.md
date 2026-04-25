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
- `g:custom_label_0` = marzovy bucket (`m-x`, `m-s`, `m-m`, `m-l`, `m-xl`) podle Shoptet exportu nakupnich cen
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
- Workflow se spousti rucne nebo externe pres `workflow_dispatch`.
- V GitHub repozitari je potreba nastavit secret `FEED_URL` s realnou URL vstupniho XML feedu.
- Pro marzove buckety je volitelny secret `SHOPTET_COSTS_URL` s URL CSV exportu nakupnich cen ze Shoptetu. Kdyz chybi nebo stazeni selze, feed se i tak vygeneruje a `g:custom_label_0` spadne na `m-x`.
- Secret `OPENAI_API_KEY` je volitelny. Kdyz nebude nastaveny, workflow i tak vygeneruje XML feed a auditni artifacty, jen bez AI optimalizace.
- AI cache z `data/cache.json` se v GitHub Actions obnovuje a uklada mezi behy, aby se stejne produkty znovu neposilaly do OpenAI.
- E-mail reporting po kazdem behu vyzaduje secrets `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` a volitelne `REPORT_EMAIL_FROM`.
- Rucni spusteni: GitHub `Actions` -> `Generate Feed` -> `Run workflow`.

## External trigger
- Workflow se ted spousti externe pres GitHub REST API `workflow_dispatch`, ne pres GitHub `schedule`.
- Workflow file musi byt na default branch repozitare.
- Minimalni vstupy pro externi trigger jsou:
  - `owner`
  - `repo`
  - workflow filename, zde `feed.yml`
  - branch `ref`
  - GitHub token s opravnenim workflow spustit
- Endpoint:
  - `POST https://api.github.com/repos/{owner}/{repo}/actions/workflows/feed.yml/dispatches`
- Ukazkovy `curl`:
```bash
curl -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/repos/Lukas-more/Shopping-feed-ai-v3/actions/workflows/feed.yml/dispatches \
  -d '{"ref":"main"}'
```
- Doporuceni: spoustej externim schedulerem vyrazne pred 07:00, napr. kolem `02:17 UTC`.
- Externi scheduler je zvolen kvuli vyssi spolehlivosti oproti GitHub `schedule`.

## GitHub Pages
- Workflow po vygenerovani feedu publikuje `data/output/optimized_feed.xml` na GitHub Pages jako stabilni `feed.xml`.
- Ocekavana URL pro tento repozitar je `https://lukas-more.github.io/Shopping-feed-ai-v3/feed.xml`.
- Pokud Pages jeste nebezi, v GitHubu otevri `Settings` -> `Pages` a jako source nastav `GitHub Actions`.
- Po uspesnem behu workflow najdes verejnou URL i v sekci `Deploy to GitHub Pages` nebo v `Settings` -> `Pages`.
- Rucni spusteni workflow zustava: `Actions` -> `Generate Feed` -> `Run workflow`.

## Prvni spusteni checklist
- V GitHub repozitari otevri `Settings` -> `Secrets and variables` -> `Actions` a zaloz secret `FEED_URL`.
- Jako hodnotu `FEED_URL` nastav: `https://www.plaza.cz/heureka/export/products.xml?hash=X4SOE1liV0PnOQmeqEid2jX`
- Pokud chces marzove buckety v `g:custom_label_0`, pridej jeste secret `SHOPTET_COSTS_URL`.
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

## Purchase prices / marze
- Workflow umi pri behu stahnout Shoptet CSV export nakupnich cen do docasneho souboru `tmp/purchase_prices.csv`; ten se necommituje do repozitare.
- CSV ma ocekavane sloupce `code`, `pairCode`, `name`, `price`, `purchasePrice`.
- Parovani probiha pres `code == g:id`.
- `purchasePrice` i `price` mohou byt s ceskou desetinnou carkou.
- Kdyz chybi `purchasePrice`, radek je neplatny nebo produkt v CSV neni, feed zapise `g:custom_label_0 = m-x`.
- Ostatni labely se pocitaji z marze `price - purchasePrice - 70 - (price * 0.05)` a do feedu se zapisuje jen `m-s`, `m-m`, `m-l` nebo `m-xl`.
- V logu a `feed_run_report.json` uvidis `products_total`, `purchase_csv_rows_loaded`, `products_with_purchase_price`, `count_custom_label_0_m_x`, `count_custom_label_0_m_s`, `count_custom_label_0_m_m`, `count_custom_label_0_m_l` a `count_custom_label_0_m_xl`.

## E-mail reporting
- Po kazdem behu workflow se odesila e-mail report na `lholer@seznam.cz`.
- Pro SMTP nastav v GitHub `Settings` -> `Secrets and variables` -> `Actions` tyto secrets: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`.
- Volitelne muzes nastavit `REPORT_EMAIL_FROM`, jinak se pouzije `SMTP_USERNAME`.
- Success report i failure report obsahuji maximum dostupnych provoznich metrik: status, cas reportu, products total, AI calls, cache hits, cache misses, `count_title_too_long`, token usage, USD cost, odkaz na `feed.xml` a odkaz na konkretni workflow run.
- Token usage a USD cost se berou z `feed_run_report.json`, ktery pipeline uklada do `data/output/`.
