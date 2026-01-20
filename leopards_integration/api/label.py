import frappe


@frappe.whitelist()
def get_leopards_slip_link(delivery_note):
    """
    Fetch Leopards slip link using Delivery Note.
    Source of truth: Leopards Shipment.
    """

    if not delivery_note:
        return None

    slip = frappe.db.get_value(
        "Leopards Shipment",
        {
            "delivery_note": delivery_note,
            "booking_status": "Booked",
        },
        "slip_link",
    )

    return slip