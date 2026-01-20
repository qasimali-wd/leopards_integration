import json
import requests
import frappe
from frappe.utils.password import get_decrypted_password


class LeopardsAPIError(Exception):
    pass


# -------------------------------------------------------------------------
# Settings & Credentials
# -------------------------------------------------------------------------

def _get_settings():
    settings = frappe.get_single("Leopards Settings")
    if not settings.enabled:
        frappe.throw("Leopards Integration is disabled in Leopards Settings.")
    return settings


def _get_api_password(settings) -> str:
    """
    Robust password retrieval for Single DocType.
    """
    try:
        pw = settings.get_password("api_password")
        if pw:
            return pw
    except Exception:
        pass

    try:
        return get_decrypted_password(
            "Leopards Settings",
            "Leopards Settings",
            "api_password",
        )
    except Exception:
        frappe.throw(
            "Unable to decrypt Leopards Settings API Password. "
            "Re-enter the password in Leopards Settings and save."
        )


# -------------------------------------------------------------------------
# Base URL Normalization (CRITICAL FIX)
# -------------------------------------------------------------------------

def _normalize_base_url(url: str) -> str:
    """
    Ensures base_url NEVER ends with /api
    Prevents /api/api/... bugs.

    Accepts:
      https://merchantapi.leopardscourier.com
      https://merchantapi.leopardscourier.com/
      https://merchantapi.leopardscourier.com/api
      https://merchantapi.leopardscourier.com/api/

    Returns:
      https://merchantapi.leopardscourier.com
    """
    if not url:
        return ""

    u = url.strip().rstrip("/")

    if u.lower().endswith("/api"):
        u = u[:-4]

    return u.rstrip("/")


def _resolve_base_url(settings) -> str:
    """
    Returns normalized Leopards base URL WITHOUT /api
    """
    if settings.base_url:
        return _normalize_base_url(settings.base_url)

    if (settings.environment or "").lower() == "production":
        return "https://merchantapi.leopardscourier.com"

    return "https://merchantapistaging.leopardscourier.com"


# -------------------------------------------------------------------------
# Booking API
# -------------------------------------------------------------------------
def book_packet(payload: dict) -> dict:
    settings = _get_settings()
    base_url = _resolve_base_url(settings)

    url = f"{base_url}/api/bookPacket/format/json/"
    api_password = _get_api_password(settings)

    payload = dict(payload)
    payload["api_key"] = settings.api_key
    payload["api_password"] = api_password

    try:
        resp = requests.post(
            url,
            data=payload,  # FORM-DATA (REQUIRED)
            timeout=30,
        )
    except requests.RequestException as e:
        raise LeopardsAPIError(f"Leopards API connection error: {e}") from e

    if resp.status_code != 200:
        raise LeopardsAPIError(
            f"Leopards HTTP {resp.status_code}: {resp.text}"
        )

    try:
        data = resp.json()
    except Exception:
        raise LeopardsAPIError(
            f"Invalid JSON response from Leopards: {resp.text}"
        )

    if str(data.get("status")) != "1":
        raise LeopardsAPIError(
            f"Leopards booking failed: {data}"
        )

    return data
# -------------------------------------------------------------------------
# Get All Cities API (OFFICIAL + SAFE)
# -------------------------------------------------------------------------

def get_all_cities() -> dict:
    """
    Leopards Get All Cities API
    Official endpoint:
      <base_url>/api/getAllCities/format/json/

    Response key MAY be:
      - city_list   (official docs)
      - data        (older / alternate responses)
    """
    settings = _get_settings()
    base_url = _resolve_base_url(settings)
    api_password = _get_api_password(settings)

    url = f"{base_url}/api/getAllCities/format/json/"

    payload = {
        "api_key": settings.api_key,
        "api_password": api_password,
    }

    try:
        resp = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
    except requests.RequestException as e:
        raise LeopardsAPIError(f"Leopards connection error: {e}") from e

    if resp.status_code != 200:
        raise LeopardsAPIError(
            f"Leopards HTTP {resp.status_code}: {resp.text}"
        )

    try:
        data = resp.json()
    except Exception:
        raise LeopardsAPIError(
            f"Invalid JSON response from Leopards: {resp.text}"
        )

    if str(data.get("status")) != "1":
        raise LeopardsAPIError(f"Leopards API error: {data}")

    return data
def print_cn(cn_number: str) -> dict:
    """
    Fetch packing slip / CN print from Leopards.

    Endpoint:
      POST <base_url>/api/printCN/format/json/

    Request:
      {
        api_key,
        api_password,
        cn_numbers: "CN123456"
      }
    """
    settings = _get_settings()
    base_url = _resolve_base_url(settings)
    api_password = _get_api_password(settings)

    url = f"{base_url}/api/printCN/format/json/"

    payload = {
        "api_key": settings.api_key,
        "api_password": api_password,
        "cn_numbers": cn_number,
    }

    try:
        resp = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
    except requests.RequestException as e:
        raise LeopardsAPIError(f"Leopards printCN connection error: {e}") from e

    if resp.status_code != 200:
        raise LeopardsAPIError(
            f"Leopards printCN HTTP {resp.status_code}: {resp.text}"
        )

    try:
        data = resp.json()
    except Exception:
        raise LeopardsAPIError(
            f"Leopards printCN invalid JSON: {resp.text}"
        )

    if str(data.get("status")) != "1":
        raise LeopardsAPIError(f"Leopards printCN failed: {data}")

    return data

#Fetch tracking details from Leopards API#

def track_packet(track_number: str) -> dict:
    """
    Fetch tracking details from Leopards API
    """
    settings = _get_settings()
    base_url = _resolve_base_url(settings)
    api_password = _get_api_password(settings)

    url = f"{base_url}/api/trackBookedPacket/format/json/"

    payload = {
        "api_key": settings.api_key,
        "api_password": api_password,
        "track_number": track_number,
    }

    try:
        resp = requests.post(
            url,
            json=payload,
            timeout=30,
        )
    except Exception as e:
        raise LeopardsAPIError(f"Tracking API error: {e}")

    if resp.status_code != 200:
        raise LeopardsAPIError(
            f"Tracking HTTP {resp.status_code}: {resp.text}"
        )

    data = resp.json()

    if str(data.get("status")) != "1":
        raise LeopardsAPIError(f"Tracking failed: {data}")

    return data
