import frappe


@frappe.whitelist()
def bulk_print_leopards_labels(delivery_notes):
    """
    Returns printable Leopards label URLs for given Delivery Notes
    """

    if isinstance(delivery_notes, str):
        delivery_notes = frappe.parse_json(delivery_notes)

    if not delivery_notes:
        frappe.throw("No Delivery Notes selected")

    urls = []
    skipped = []

    for dn_name in delivery_notes:
        # 1️⃣ Find shipment by Delivery Note
        shipment = frappe.db.get_value(
            "Leopards Shipment",
            {"delivery_note": dn_name, "booking_status": "Booked"},
            ["slip_link", "cn_number"],
            as_dict=True,
        )

        if shipment and shipment.slip_link:
            urls.append(shipment.slip_link)
            continue

        # 2️⃣ Fallback: Delivery Note custom field (if you keep it)
        dn = frappe.get_doc("Delivery Note", dn_name)
        if dn.get("custom_leopards_slip_link"):
            urls.append(dn.custom_leopards_slip_link)
            continue

        skipped.append(dn_name)

    return {
        "urls": urls,
        "skipped": skipped,
    }