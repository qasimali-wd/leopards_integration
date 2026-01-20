import requests
import frappe
from leopards_integration.utils.leopards_client import (
    _get_settings,
    _get_api_password,
    _resolve_base_url,
    LeopardsAPIError,
)


DELIVERED_KEYWORDS = {
    "delivered",
    "shipment delivered",
    "consignment delivered",
}


def _is_delivered(status_text: str) -> bool:
    if not status_text:
        return False
    s = status_text.lower()
    return any(k in s for k in DELIVERED_KEYWORDS)


def fetch_leopards_tracking(cn: str) -> str:
    """
    Fetch current tracking status from Leopards.
    Best-effort: NEVER raises for API instability.
    """

    settings = _get_settings()
    base_url = _resolve_base_url(settings)
    api_password = _get_api_password(settings)

    url = f"{base_url}/api/trackBookedPacket/format/json/"

    payload = {
        "api_key": settings.api_key,
        "api_password": api_password,
        "track_numbers": [cn],
    }

    try:
        resp = requests.post(
            url,
            json=payload,
            timeout=30,
            headers={"User-Agent": "ERPNext-Leopards-Tracking"},
        )
    except Exception:
        return "Pending"

    # Leopards tracking API is unstable → treat as pending
    if resp.status_code != 200:
        return "Pending"

    try:
        data = resp.json()
    except Exception:
        return "Pending"

    if str(data.get("status")) != "1":
        return "Pending"

    packets = data.get("packet_list") or []
    if not packets:
        return "Pending"

    latest = packets[0]

    return (
        latest.get("current_status")
        or latest.get("status")
        or "Pending"
    )
