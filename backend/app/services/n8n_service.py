from __future__ import annotations

import requests


def trigger_webhook(url: str | None, payload: dict) -> bool:
    if not url:
        return False
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.ok
    except requests.RequestException:
        return False
