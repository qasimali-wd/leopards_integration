import frappe
from frappe.utils import now_datetime
from leopards_integration.api.tracking import (
    fetch_leopards_tracking,
    _is_delivered,
)


def _log_tracking_event(delivery_note, cn, status):
    """
    Insert tracking history only if status changed.
    """

    last = frappe.db.get_value(
        "Leopards Tracking Event",
        {"delivery_note": delivery_note},
        "status_text",
        order_by="creation desc",
    )

    if last == status:
        return  # No change → no history row

    frappe.get_doc({
        "doctype": "Leopards Tracking Event",
        "delivery_note": delivery_note,
        "cn_number": cn,
        "status_text": status,
        "event_time": now_datetime(),
        "source": "Leopards API",
    }).insert(ignore_permissions=True)


def sync_leopards_tracking(limit=50):
    """
    Scheduler-safe tracking sync with history.
    """

    rows = frappe.get_all(
        "Leopards Shipment Tracking",
        filters={"is_delivered": 0},
        fields=[
            "name",
            "delivery_note",
            "cn_number",
            "current_status",
        ],
        limit=int(limit),
    )

    for row in rows:
        try:
            status = fetch_leopards_tracking(row.cn_number)
        except Exception:
            continue

        delivered = _is_delivered(status)

        # Only act if status changed
        if status != row.current_status:
            # Snapshot update
            frappe.db.set_value(
                "Leopards Shipment Tracking",
                row.name,
                {
                    "current_status": status,
                    "last_updated": now_datetime(),
                    "is_delivered": delivered,
                },
            )

            # History insert
            _log_tracking_event(
                row.delivery_note,
                row.cn_number,
                status,
            )

            # Optional DN summary (safe)
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