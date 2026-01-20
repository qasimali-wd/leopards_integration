import frappe
from frappe import _

from leopards_integration.utils.leopards_client import get_all_cities


@frappe.whitelist()
def sync_leopards_cities():
    """
    Sync Leopards cities into DocType `Leopards City`.

    Handles BOTH known Leopards response formats:
      - city_list (official docs)
      - data      (older / alternate responses)
    """
    resp = get_all_cities()

    # ------------------------------------------------------------------
    # Leopards RESPONSE NORMALIZATION (CRITICAL FIX)
    # ------------------------------------------------------------------
    rows = resp.get("city_list")
    if not isinstance(rows, list):
        rows = resp.get("data")

    rows = rows or []

    if not rows:
        return {
            "status": "success",
            "upserted": 0,
            "total_from_api": 0,
            "message": "City API reachable but returned empty list.",
        }

    upserted = 0
    seen_ids = set()

    for r in rows:
        # Support BOTH response shapes
        city_id = str(
            r.get("id")
            or r.get("city_id")
            or ""
        ).strip()

        city_name = str(
            r.get("name")
            or r.get("city_name")
            or ""
        ).strip()

        if not city_id or not city_name:
            continue

        seen_ids.add(city_id)

        allow_origin = 1 if str(r.get("allow_as_origin") or "0") in ("1", "true", "True") else 0
        allow_dest = 1 if str(r.get("allow_as_destination") or "0") in ("1", "true", "True") else 0

        if frappe.db.exists("Leopards City", city_id):
            doc = frappe.get_doc("Leopards City", city_id)
            doc.city_name = city_name
            doc.allow_as_origin = allow_origin
            doc.allow_as_destination = allow_dest
            doc.is_active = 1
            doc.save(ignore_permissions=True)
        else:
            doc = frappe.new_doc("Leopards City")
            doc.city_id = city_id   # autoname = field:city_id
            doc.city_name = city_name
            doc.allow_as_origin = allow_origin
            doc.allow_as_destination = allow_dest
            doc.is_active = 1
            doc.insert(ignore_permissions=True)

        upserted += 1

    frappe.db.commit()

    return {
        "status": "success",
        "upserted": upserted,
        "total_from_api": len(rows),
    }
