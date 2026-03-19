import requests


def download_feed(url: str) -> str:
    response = requests.get(url, timeout=90)
    response.raise_for_status()
    response.encoding = response.encoding or "utf-8"
    return response.text
