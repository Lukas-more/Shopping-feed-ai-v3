from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

from openai import APITimeoutError, APIConnectionError, RateLimitError, APIError
from requests import RequestException

from src.feed.downloader import download_feed
from src.feed.parser import parse_heureka_feed
from src.feed.writer import build_gmc_feed
from src.feed.audit import build_audit_rows, write_audit_csv
from src.feed.qa import build_qa_report
from src.labels.price_bucket import compute_price_buckets
from src.labels.margin import load_margin_map
from src.utils.hashing import product_hash
from src.ai.prompts import load_templates, build_prompt
from src.ai.client import OpenAIOptimizer, estimate_cost, UsageCost


ROOT = Path(__file__).resolve().parents[2]
ESTIMATED_SECONDS_PER_AI_CALL = 4.0


def load_settings(settings_path: str) -> dict:
    with open(settings_path, "r", encoding="utf-8") as f:
        return json.load(f)


def is_active_for_ai(product, active_max: int) -> bool:
    try:
        dd = int((product.delivery_date or "999").strip())
    except ValueError:
        return False
    return dd <= active_max


def _cache_context_key(settings: dict, template_key: str, expected_output_tokens: int) -> str:
    payload = {
        "model": settings.get("model", "gpt-4o-mini"),
        "prompt_template": template_key,
        "custom_prompt": settings.get("custom_prompt", ""),
        "expected_output_tokens": expected_output_tokens,
        "optimize_title": settings.get("optimize_title", True),
        "optimize_description": settings.get("optimize_description", True),
        "optimize_product_type": settings.get("optimize_product_type", True),
        "generate_intent_label": settings.get("generate_intent_label", True),
        "generate_segment_label": settings.get("generate_segment_label", True),
    }
    return hashlib.md5(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _resolve_max_ai_products(settings: dict) -> int | None:
    raw_value = os.getenv("MAX_AI_PRODUCTS", settings.get("max_ai_products", ""))
    if raw_value in ("", None):
        return None
    try:
        limit = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError("MAX_AI_PRODUCTS musi byt cele nezaporne cislo.") from exc
    if limit < 0:
        raise ValueError("MAX_AI_PRODUCTS musi byt cele nezaporne cislo.")
    return limit


def _write_json_with_fallback(output_path: Path, payload: dict) -> tuple[Path, str | None]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return output_path, None
    except PermissionError:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        fallback_path = output_path.with_name(f"{output_path.stem}_{timestamp}{output_path.suffix}")
        fallback_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        warning = f"QA report byl zamceny, zapis pouzit do nahradniho souboru {fallback_path.name}."
        return fallback_path, warning


def _write_xml_with_fallback(tree, output_path: Path) -> tuple[Path, str | None]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        tree.write(
            str(output_path),
            encoding="utf-8",
            xml_declaration=True,
            pretty_print=True,
        )
        return output_path, None
    except PermissionError:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        fallback_path = output_path.with_name(f"{output_path.stem}_{timestamp}{output_path.suffix}")
        tree.write(
            str(fallback_path),
            encoding="utf-8",
            xml_declaration=True,
            pretty_print=True,
        )
        warning = f"XML feed byl zamceny, zapis pouzit do nahradniho souboru {fallback_path.name}."
        return fallback_path, warning


def run_pipeline(settings: dict, api_key: str | None = None, dry_run: bool = False) -> dict:
    try:
        feed_xml = download_feed(settings["feed_url"])
    except RequestException as exc:
        raise RuntimeError("Nepodarilo se stahnout vstupni feed. Zkontroluj URL feedu a pripojeni k internetu.") from exc
    products = parse_heureka_feed(feed_xml)
    price_buckets = compute_price_buckets(products)
    margin_map = load_margin_map(settings.get("margin_csv_path", ""))

    cache_path = ROOT / settings.get("cache_path", "data/cache.json")
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    else:
        cache = {}

    templates = load_templates(ROOT / "config" / "prompt_templates.json")

    template_key = settings.get("prompt_template", "default_cz_shopping")
    template = templates[template_key]

    system_prompt = template["system_prompt"]
    user_prompt_template = template["user_prompt"]
    expected_output_tokens = int(template.get("expected_output_tokens", 220))

    if settings.get("custom_prompt"):
        user_prompt_template = settings["custom_prompt"]
        expected_output_tokens = int(settings.get("expected_output_tokens", expected_output_tokens))

    cache_context = _cache_context_key(settings, template_key, expected_output_tokens)
    max_ai_products = _resolve_max_ai_products(settings)
    max_ai_products_explicit = max_ai_products is not None

    optimizer = OpenAIOptimizer(
        api_key=api_key,
        model=settings.get("model", "gpt-4o-mini"),
    ) if api_key and not dry_run else None

    optimized_map = {}
    estimated = UsageCost()
    actual = UsageCost()
    cache_hits = 0
    cache_misses = 0
    cache_miss_reasons = {
        "missing_entry": 0,
        "hash_changed": 0,
        "context_changed": 0,
    }
    active_products = 0
    skipped_inactive = 0
    ai_candidates = 0
    ai_attempted = 0
    ai_calls = 0
    ai_errors = 0
    ai_skipped_missing_key = 0
    ai_skipped_due_limit = 0

    for index, p in enumerate(products, start=1):
        h = product_hash(p)
        active = is_active_for_ai(p, int(settings.get("delivery_date_active_max", 1)))

        cached_entry = cache.get(p.item_id)
        if (
            cached_entry
            and cached_entry.get("hash") == h
            and cached_entry.get("context") == cache_context
        ):
            cached_data = dict(cache[p.item_id].get("data", {}))
            cached_data["_ai_used"] = False
            cached_data["_ai_success"] = bool(cache[p.item_id].get("data"))
            optimized_map[p.item_id] = cached_data
            cache_hits += 1
            continue

        cache_misses += 1
        if not cached_entry:
            cache_miss_reasons["missing_entry"] += 1
        elif cached_entry.get("hash") != h:
            cache_miss_reasons["hash_changed"] += 1
        else:
            cache_miss_reasons["context_changed"] += 1

        if not active:
            optimized_map.setdefault(p.item_id, {})
            optimized_map[p.item_id]["_ai_used"] = False
            optimized_map[p.item_id]["_ai_success"] = False
            skipped_inactive += 1
            continue

        active_products += 1

        user_prompt = build_prompt(user_prompt_template, p)

        estimate = estimate_cost(
            settings.get("model", "gpt-4o-mini"),
            user_prompt,
            expected_output_tokens=expected_output_tokens,
        )
        estimated.input_tokens += estimate.input_tokens
        estimated.output_tokens += estimate.output_tokens
        estimated.cost_usd += estimate.cost_usd
        ai_candidates += 1

        if optimizer is None:
            optimized_map.setdefault(p.item_id, {})
            optimized_map[p.item_id]["_ai_used"] = False
            optimized_map[p.item_id]["_ai_success"] = False
            ai_skipped_missing_key += 1
            continue

        if max_ai_products is not None and ai_attempted >= max_ai_products:
            optimized_map.setdefault(p.item_id, {})
            optimized_map[p.item_id]["_ai_used"] = False
            optimized_map[p.item_id]["_ai_success"] = False
            ai_skipped_due_limit += 1
            continue

        ai_attempted += 1
        try:
            data, usage = optimizer.optimize_json(system_prompt, user_prompt)
        except (APITimeoutError, APIConnectionError, RateLimitError, APIError, ValueError) as e:
            print(f"[AI ERROR] Produkt {p.item_id}: {e}")
            optimized_map.setdefault(p.item_id, {})
            optimized_map[p.item_id]["_ai_used"] = True
            optimized_map[p.item_id]["_ai_success"] = False
            ai_errors += 1
            continue
        except Exception as e:
            print(f"[UNEXPECTED ERROR] Produkt {p.item_id}: {e}")
            optimized_map.setdefault(p.item_id, {})
            optimized_map[p.item_id]["_ai_used"] = True
            optimized_map[p.item_id]["_ai_success"] = False
            ai_errors += 1
            continue

        optimized_map[p.item_id] = dict(data)
        optimized_map[p.item_id]["_ai_used"] = True
        optimized_map[p.item_id]["_ai_success"] = True
        cache[p.item_id] = {
            "hash": h,
            "context": cache_context,
            "data": data,
        }

        actual.input_tokens += usage.input_tokens
        actual.output_tokens += usage.output_tokens
        actual.cost_usd += usage.cost_usd
        ai_calls += 1

        if ai_calls % 10 == 0:
            cache_path.write_text(
                json.dumps(cache, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    output_path = ROOT / settings.get("output_path", "data/output/optimized_feed.xml")
    qa_report_path = output_path.with_name("feed_qa_report.json")
    audit_csv_path = output_path.with_name("feed_audit.csv")
    run_report_path = output_path.with_name("feed_run_report.json")

    tree = build_gmc_feed(
        products,
        optimized_map,
        price_buckets,
        margin_map,
        int(settings.get("default_margin_percent", 40)),
        settings.get("currency", "CZK"),
    )

    xml_warning: str | None = None
    final_output_path = output_path
    if optimizer is not None:
        cache_path.write_text(
            json.dumps(cache, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if not dry_run:
        final_output_path, xml_warning = _write_xml_with_fallback(tree, output_path)

    estimated_seconds = round(ai_candidates * ESTIMATED_SECONDS_PER_AI_CALL)
    estimated_minutes_low = round((ai_candidates * 2.5) / 60, 1)
    estimated_minutes_high = round((ai_candidates * 6.0) / 60, 1)
    warnings: list[str] = []

    run_stats = {
        "products_total": len(products),
        "cache_entries": len(cache),
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "products_skipped_inactive": skipped_inactive,
        "products_needing_refresh": active_products,
        "ai_selected_count": ai_candidates,
        "ai_candidates": ai_candidates,
        "ai_attempted": ai_attempted,
        "ai_calls": ai_calls,
        "ai_errors": ai_errors,
        "ai_skipped_missing_key": ai_skipped_missing_key,
        "ai_skipped_due_limit": ai_skipped_due_limit,
        "max_ai_products": max_ai_products,
        "max_ai_products_explicit": max_ai_products_explicit,
        "cache_miss_reasons": cache_miss_reasons,
        "estimated_runtime_seconds": estimated_seconds,
        "estimated_runtime_minutes_range": f"{estimated_minutes_low}-{estimated_minutes_high}",
        "estimated_input_tokens": estimated.input_tokens,
        "estimated_output_tokens": estimated.output_tokens,
        "estimated_cost_usd": round(estimated.cost_usd, 6),
        "actual_input_tokens": actual.input_tokens,
        "actual_output_tokens": actual.output_tokens,
        "actual_cost_usd": round(actual.cost_usd, 6),
        "output_path": str(final_output_path),
    }

    qa_report = build_qa_report(products, optimized_map, run_stats)
    audit_rows = build_audit_rows(products, optimized_map)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_audit_csv_path, audit_warning = write_audit_csv(audit_rows, audit_csv_path)
    final_qa_report_path, qa_warning = _write_json_with_fallback(qa_report_path, qa_report)
    if audit_warning:
        warnings.append(audit_warning)
    if qa_warning:
        warnings.append(qa_warning)
    if xml_warning:
        warnings.append(xml_warning)

    run_stats["qa_report"] = qa_report
    run_stats["qa_report_path"] = str(final_qa_report_path)
    run_stats["audit_csv_path"] = str(final_audit_csv_path)
    run_stats["run_report_path"] = str(run_report_path)
    run_stats["warnings"] = warnings
    if ai_skipped_due_limit:
        warnings.append(
            f"Dosazen limit MAX_AI_PRODUCTS={max_ai_products}; cast produktu byla preskocena bez AI."
        )
    final_run_report_path, run_report_warning = _write_json_with_fallback(run_report_path, run_stats)
    if run_report_warning:
        warnings.append(run_report_warning)
        run_stats["warnings"] = warnings
        run_stats["run_report_path"] = str(final_run_report_path)
    print(
        "[RUN SUMMARY] "
        f"products_total={run_stats['products_total']} "
        f"cache_hits={cache_hits} "
        f"cache_misses={cache_misses} "
        f"cache_miss_reasons={json.dumps(cache_miss_reasons, ensure_ascii=False)} "
        f"skipped_inactive={skipped_inactive} "
        f"ai_candidates={ai_candidates} "
        f"ai_attempted={ai_attempted} "
        f"ai_calls={ai_calls} "
        f"ai_errors={ai_errors} "
        f"ai_skipped_missing_key={ai_skipped_missing_key} "
        f"ai_skipped_due_limit={ai_skipped_due_limit} "
        f"max_ai_products={max_ai_products} "
        f"max_ai_products_explicit={max_ai_products_explicit}"
    )
    return run_stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--settings", required=True)
    parser.add_argument("--api-key", default=os.getenv("OPENAI_API_KEY", ""))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = run_pipeline(
        load_settings(args.settings),
        api_key=args.api_key or None,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
