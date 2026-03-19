import csv


def load_margin_map(csv_path: str) -> dict[str, str]:
    if not csv_path:
        return {}
    mapping: dict[str, str] = {}
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            item_id = (row.get("ITEM_ID") or row.get("item_id") or "").strip()
            margin = (row.get("margin_percent") or row.get("margin") or "").strip()
            if item_id and margin:
                mapping[item_id] = f"margin_{margin.replace('%','').strip()}"
    return mapping


def margin_label(item_id: str, default_margin_percent: int, mapping: dict[str, str] | None = None) -> str:
    mapping = mapping or {}
    return mapping.get(item_id, f"margin_{int(default_margin_percent)}")
