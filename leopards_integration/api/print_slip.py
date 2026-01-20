import frappe
import requests
from leopards_integration.utils.leopards_client import print_cn


@frappe.whitelist()
def generate_packing_slip(shipment_name):
    shipment = frappe.get_doc("Leopards Shipment", shipment_name)

    if not shipment.cn_number:
        frappe.throw("CN number is missing. Book the shipment first.")

    # Prevent duplicate generation
    if shipment.slip_generated and shipment.packing_slip:
        return {
            "status": "success",
            "message": "Packing slip already generated.",
            "file": shipment.packing_slip,
        }

    resp = print_cn(shipment.cn_number)

    # -------------------------------------------------------
    # Case 1: Leopards returns a printable URL
    # -------------------------------------------------------
    if resp.get("print_url"):
        file = frappe.get_doc({
            "doctype": "File",
            "file_url": resp["print_url"],
            "attached_to_doctype": "Leopards Shipment",
            "attached_to_name": shipment.name,
            "is_private": 0,
        })
        file.insert(ignore_permissions=True)

        shipment.packing_slip = file.file_url
        shipment.slip_generated = 1
        shipment.save(ignore_permissions=True)

        return {"status": "success", "type": "url"}

    # -------------------------------------------------------
    # Case 2: Leopards returns raw HTML
    # -------------------------------------------------------
    if resp.get("html"):
        file = frappe.get_doc({
            "doctype": "File",
            "file_name": f"{shipment.cn_number}.html",
            "content": resp["html"],
            "attached_to_doctype": "Leopards Shipment",
            "attached_to_name": shipment.name,
            "is_private": 0,
        })
        file.insert(ignore_permissions=True)

        shipment.packing_slip = file.file_url
        shipment.slip_generated = 1
        shipment.save(ignore_permissions=True)

        return {"status": "success", "type": "html"}

    frappe.throw("Unsupported packing slip format returned by Leopards.")
