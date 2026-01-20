import frappe
from frappe.utils import now_datetime
from leopards_integration.api.tracking import (
    fetch_leopards_tracking,
    _is_delivered,
)


@frappe.whitelist()
def backfill_leopards_tracking(limit=200):
    """
    ONE-TIME backfill.
    Never fails due to Leopards API instability.
    """

    dns = frappe.get_all(
        "Delivery Note",
        filters={
            "custom_leopards_booking_status": "Booked",
            "custom_leopards_consignment_number": ["is", "set"],
        },
        fields=["name", "custom_leopards_consignment_number"],
        limit=int(limit),
    )

    created = 0
    skipped = 0

    for d in dns:
        if frappe.db.exists(
            "Leopards Shipment Tracking",
            {"delivery_note": d.name},
        ):
            skipped += 1
            continue

        # Best-effort tracking
        try:
            status = fetch_leopards_tracking(
                d.custom_leopards_consignment_number
            )
        except Exception:
            status = "Pending"

        delivered = _is_delivered(status)

        frappe.get_doc({
            "doctype": "Leopards Shipment Tracking",
            "delivery_note": d.name,
            "cn_number": d.custom_leopards_consignment_number,
            "current_status": status,
            "last_updated": now_datetime(),
            "is_delivered": delivered,
        }).insert(ignore_permissions=True)

        created += 1

    frappe.db.commit()

    return {
        "created": created,
        "skipped_existing": skipped,
        "total_seen": len(dns),
    }
