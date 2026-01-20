import frappe
from frappe.utils import now_datetime
from leopards_integration.api.tracking import (
    fetch_leopards_tracking,
    _is_delivered,
)


def sync_leopards_tracking(limit=50):
    """
    Scheduler-safe tracking sync.

    Rules:
    - Only sync undelivered shipments
    - Stop forever once delivered
    - Never fail due to API instability
    """

    rows = frappe.get_all(
        "Leopards Shipment Tracking",
        filters={"is_delivered": 0},
        fields=["name", "delivery_note", "cn_number"],
        limit=int(limit),
    )

    for row in rows:
        try:
            status = fetch_leopards_tracking(row.cn_number)
        except Exception:
            # Best-effort only
            continue

        delivered = _is_delivered(status)

        # Update tracking row
        frappe.db.set_value(
            "Leopards Shipment Tracking",
            row.name,
            {
                "current_status": status,
                "last_updated": now_datetime(),
                "is_delivered": delivered,
            },
        )

        # OPTIONAL summary back to DN (safe, no booking_status change)
        frappe.db.set_value(
            "Delivery Note",
            row.delivery_note,
            {
                "custom_leopards_last_tracking_status": status,
                "custom_leopards_delivered_on": now_datetime()
                if delivered else None,
            },
            update_modified=False,
        )

    frappe.db.commit()