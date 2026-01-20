import frappe
from frappe.utils import now_datetime
from leopards_integration.api.tracking_client import fetch_leopards_tracking, is_delivered


def sync_leopards_tracking():
    dns = frappe.get_all(
        "Delivery Note",
        filters={
            "custom_leopards_booking_status": "Booked",
            "custom_leopards_delivered_on": ["is", "not set"],
        },
        fields=["name", "custom_leopards_consignment_number"],
        limit=500,
    )

    for d in dns:
        cn = d.custom_leopards_consignment_number
        if not cn:
            continue

        try:
            status = fetch_leopards_tracking(cn)
            delivered = is_delivered(status)

            # Upsert tracking table
            existing = frappe.db.get_value(
                "Leopards Shipment Tracking",
                {"delivery_note": d.name},
                "name",
            )

            values = {
                "delivery_note": d.name,
                "cn_number": cn,
                "current_status": status,
                "last_updated": now_datetime(),
                "is_delivered": delivered,
            }

            if existing:
                frappe.db.set_value("Leopards Shipment Tracking", existing, values)
            else:
                frappe.get_doc({
                    "doctype": "Leopards Shipment Tracking",
                    **values,
                }).insert(ignore_permissions=True)

            # Update DN summary
            frappe.db.set_value(
                "Delivery Note",
                d.name,
                {
                    "custom_leopards_last_tracking_status": status,
                    "custom_leopards_delivered_on": now_datetime() if delivered else None,
                },
            )

        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                "Leopards Tracking Sync Failed",
            )
