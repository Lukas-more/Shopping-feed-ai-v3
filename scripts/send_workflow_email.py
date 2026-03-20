from __future__ import annotations

import json
import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from zoneinfo import ZoneInfo


DEFAULT_TO = "lholer@seznam.cz"


def _load_json(path_value: str) -> dict:
    path = Path(path_value)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _pages_feed_url() -> str:
    repository = os.getenv("GITHUB_REPOSITORY", "")
    if "/" not in repository:
        return ""
    owner, repo = repository.split("/", 1)
    return f"https://{owner.lower()}.github.io/{repo}/feed.xml"


def _run_url() -> str:
    server_url = os.getenv("GITHUB_SERVER_URL", "https://github.com")
    repository = os.getenv("GITHUB_REPOSITORY", "")
    run_id = os.getenv("GITHUB_RUN_ID", "")
    if not repository or not run_id:
        return ""
    return f"{server_url}/{repository}/actions/runs/{run_id}"


def _format_value(value: object, fallback: str = "n/a") -> str:
    if value in ("", None):
        return fallback
    return str(value)


def build_subject(status: str) -> str:
    repository = os.getenv("GITHUB_REPOSITORY", "shopping-feed-ai-v3")
    return f"[{repository}] Feed run {status}"


def build_body(status: str, run_report: dict, qa_report: dict) -> str:
    now_prague = datetime.now(ZoneInfo("Europe/Prague")).strftime("%Y-%m-%d %H:%M:%S %Z")
    feed_url = _pages_feed_url()
    run_url = _run_url()

    products_total = run_report.get("products_total", qa_report.get("products_total"))
    ai_calls = run_report.get("ai_calls", qa_report.get("ai_calls"))
    cache_hits = run_report.get("cache_hits")
    cache_misses = run_report.get("cache_misses")
    title_too_long = qa_report.get("count_title_too_long")
    input_tokens = run_report.get("actual_input_tokens")
    output_tokens = run_report.get("actual_output_tokens")
    total_tokens = None
    if input_tokens is not None or output_tokens is not None:
        total_tokens = (input_tokens or 0) + (output_tokens or 0)
    usd_cost = run_report.get("actual_cost_usd")
    estimated_usd_cost = run_report.get("estimated_cost_usd")

    cost_label = "actual_cost_usd"
    cost_value = usd_cost
    if cost_value in (None, ""):
        cost_label = "estimated_cost_usd"
        cost_value = estimated_usd_cost

    lines = [
        f"Status: {status}",
        f"Report time: {now_prague}",
        f"Products total: {_format_value(products_total)}",
        f"AI calls: {_format_value(ai_calls)}",
        f"Cache hits: {_format_value(cache_hits)}",
        f"Cache misses: {_format_value(cache_misses)}",
        f"count_title_too_long: {_format_value(title_too_long)}",
        f"Input tokens: {_format_value(input_tokens)}",
        f"Output tokens: {_format_value(output_tokens)}",
        f"Total tokens: {_format_value(total_tokens)}",
        f"{cost_label}: {_format_value(cost_value)}",
        f"Feed URL: {_format_value(feed_url)}",
        f"Workflow run: {_format_value(run_url)}",
    ]

    if status != "success" and not run_report:
        lines.append("Run report was not generated, likely because the workflow failed before the feed pipeline completed.")

    return "\n".join(lines)


def send_email(subject: str, body: str) -> None:
    smtp_host = os.environ["SMTP_HOST"]
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.environ["SMTP_USERNAME"]
    smtp_password = os.environ["SMTP_PASSWORD"]
    sender = os.getenv("REPORT_EMAIL_FROM", smtp_username)
    recipient = os.getenv("REPORT_EMAIL_TO", DEFAULT_TO)

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient
    message.set_content(body)

    if smtp_port == 465:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30) as server:
            server.login(smtp_username, smtp_password)
            server.send_message(message)
        return

    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(message)


def main() -> None:
    status = os.getenv("WORKFLOW_STATUS", "unknown")
    run_report = _load_json(os.getenv("RUN_REPORT_PATH", "data/output/feed_run_report.json"))
    qa_report = _load_json(os.getenv("QA_REPORT_PATH", "data/output/feed_qa_report.json"))
    subject = build_subject(status)
    body = build_body(status, run_report, qa_report)
    send_email(subject, body)
    print(f"Email report sent with status={status}")


if __name__ == "__main__":
    main()
