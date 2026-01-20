import json
import frappe
from frappe import _

from leopards_integration.services.shipment_builder import (
    build_leopards_shipment,
    build_book_packet_payload,
)
from leopards_integration.utils.leopards_client import (
    book_packet,
    LeopardsAPIError,
)


@frappe.whitelist()
def book_from_delivery_note(delivery_note):
    if not delivery_note:
        frappe.throw("delivery_note is required")

    shipment = None

    try:
        # 1. Create Shipment (Draft forever)
        shipment = build_leopards_shipment(delivery_note)

        # 2. Build payload
        payload = build_book_packet_payload(shipment)

        # 3. Call Leopards
        response = book_packet(payload)

        shipment.response_payload = json.dumps(response, indent=2)

        cn_number = response.get("track_number")
        slip_link = response.get("slip_link")

        if not cn_number:
            raise LeopardsAPIError(f"track_number missing: {response}")

        # 4. Update Shipment
        shipment.cn_number = str(cn_number)
        shipment.slip_link = str(slip_link or "")
        shipment.booking_status = "Booked"
        shipment.last_error = ""
        shipment.save(ignore_permissions=True)

        # 5. Update Delivery Note
        dn = frappe.get_doc("Delivery Note", delivery_note)
        dn.custom_leopards_consignment_number = shipment.cn_number
        dn.custom_leopards_slip_link = shipment.slip_link
        dn.custom_leopards_booking_status = "Booked"
        dn.custom_leopards_last_tracking_status = "Booked"
        dn.save(ignore_permissions=True)

        return {
            "status": "Booked",
            "cn_number": shipment.cn_number,
            "slip_link": shipment.slip_link,
            "shipment": shipment.name,
        }

    except Exception as e:
        if shipment:
            shipment.booking_status = "Failed"
            shipment.last_error = str(e)[:240]
            shipment.save(ignore_permissions=True)

        frappe.throw(_("Leopards booking failed: {0}").format(str(e)))
