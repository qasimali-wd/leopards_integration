import time
import frappe
from leopards_integration.api.booking import book_from_delivery_note


@frappe.whitelist()
def bulk_book_delivery_notes(delivery_notes):
    """
    Queue bulk booking of Delivery Notes to Leopards.
    This function is called from List View.
    """

    if isinstance(delivery_notes, str):
        delivery_notes = frappe.parse_json(delivery_notes)

    if not delivery_notes:
        frappe.throw("No Delivery Notes selected")

    frappe.enqueue(
        method="leopards_integration.api.bulk_booking.bulk_book_delivery_notes_job",
        queue="long",
        timeout=3600,
        delivery_notes=delivery_notes,
        user=frappe.session.user,
    )

    return {
        "status": "queued",
        "count": len(delivery_notes),
    }


def bulk_book_delivery_notes_job(delivery_notes, user):
    """
    Background worker job
    """
    frappe.set_user(user)

    results = {
        "booked": [],
        "skipped": [],
        "failed": [],
    }

    for dn_name in delivery_notes:
        try:
            dn = frappe.get_doc("Delivery Note", dn_name)

            if dn.docstatus != 1:
                results["skipped"].append({
                    "dn": dn_name,
                    "reason": "Not submitted",
                })
                continue

            if (dn.get("custom_leopards_booking_status") or "") == "Booked":
                results["skipped"].append({
                    "dn": dn_name,
                    "reason": "Already booked",
                })
                continue

            # 🔒 API THROTTLE (MANDATORY)
            time.sleep(1)

            res = book_from_delivery_note(dn_name)

            results["booked"].append({
                "dn": dn_name,
                "cn": res.get("cn_number") or "",
            })

        except Exception:
            frappe.log_error(
                title="Leopards Bulk Booking Failed",
                message=f"{dn_name}\n{frappe.get_traceback()}",
            )

            results["failed"].append({
                "dn": dn_name,
                "error": "See Error Log",
            })

    frappe.publish_realtime(
        event="leopards_bulk_booking_done",
        message=results,
        user=user,
    )