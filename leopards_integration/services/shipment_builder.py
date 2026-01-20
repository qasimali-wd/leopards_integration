import json
import frappe
from frappe.utils import flt


# =====================================================
# SETTINGS
# =====================================================

def get_leopards_settings():
    return frappe.get_single("Leopards Settings")


# =====================================================
# ADDRESS HELPERS (ERPNext-CORRECT)
# =====================================================

def get_shipping_address(dn):
    address_name = (
        dn.shipping_address_name
        or dn.customer_address
    )

    if not address_name:
        address_name = frappe.db.get_value(
            "Dynamic Link",
            {
                "link_doctype": "Customer",
                "link_name": dn.customer,
                "parenttype": "Address",
            },
            "parent",
        )

    if not address_name:
        frappe.throw(
            "Shipping Address not found. "
            "Set Shipping Address on Delivery Note or Customer."
        )

    return frappe.get_doc("Address", address_name)


def compose_address(addr):
    parts = [
        addr.address_line1,
        addr.address_line2,
        addr.city,
        addr.state,
        addr.pincode,
        addr.country,
    ]
    return ", ".join([p for p in parts if p])


def get_phone(addr, dn):
    if addr.phone:
        return addr.phone.strip()

    return (frappe.db.get_value("Customer", dn.customer, "mobile_no") or "").strip()


# =====================================================
# WEIGHT RESOLUTION (GRAMS ONLY – NO CONVERSION)
# =====================================================

def resolve_shipment_weight_grams(dn):
    """
    Resolve shipment weight in GRAMS.

    Rules:
    - DN.total_net_weight is assumed to be GRAMS
    - Item.weight_per_unit is assumed to be GRAMS
    - NO kg→g conversion
    - FAIL if missing
    """

    # 1️⃣ DN-level weight (grams)
    if dn.get("total_net_weight"):
        w = int(round(float(dn.total_net_weight)))
        if w > 0:
            return w

    # 2️⃣ Sum item weights (grams)
    total = 0
    for item in dn.items:
        w = float(item.get("weight_per_unit") or 0)
        q = float(item.get("qty") or 0)
        total += w * q

    total = int(round(total))
    if total > 0:
        return total

    frappe.throw(
        "Shipment weight is missing.\n"
        "Set Delivery Note Total Net Weight (grams) or Item Weight Per Unit (grams)."
    )


# =====================================================
# CITY RESOLUTION
# =====================================================

def resolve_leopards_city_id(city_value: str, for_origin=False) -> str:
    if not city_value:
        frappe.throw("City is missing.")

    city_value = str(city_value).strip()

    if frappe.db.exists("Leopards City", city_value):
        doc = frappe.get_doc("Leopards City", city_value)
        if for_origin and not doc.allow_as_origin:
            frappe.throw(f"{doc.city_name} not allowed as origin")
        if not for_origin and not doc.allow_as_destination:
            frappe.throw(f"{doc.city_name} not allowed as destination")
        return doc.name

    row = frappe.db.get_value(
        "Leopards City",
        {"city_name": city_value, "is_active": 1},
        ["name", "allow_as_origin", "allow_as_destination"],
        as_dict=True,
    )

    if not row:
        frappe.throw(f"City '{city_value}' not mapped for Leopards")

    if for_origin and not row.allow_as_origin:
        frappe.throw(f"{city_value} not allowed as origin")
    if not for_origin and not row.allow_as_destination:
        frappe.throw(f"{city_value} not allowed as destination")

    return row.name


# =====================================================
# BUILD LEOPARDS SHIPMENT (DRAFT)
# =====================================================

def build_leopards_shipment(delivery_note_name):
    dn = frappe.get_doc("Delivery Note", delivery_note_name)

    if dn.docstatus != 1:
        frappe.throw("Delivery Note must be submitted")

    settings = get_leopards_settings()
    addr = get_shipping_address(dn)

    shipment = frappe.new_doc("Leopards Shipment")
    shipment.docstatus = 0
    shipment.booking_status = "Draft"

    shipment.delivery_note = dn.name
    shipment.customer = dn.customer
    shipment.company = dn.company

# Prefer real customer name, not address title
consignee_name = (dn.customer_name or "").strip()

if not consignee_name:
    consignee_name = (frappe.db.get_value("Customer", dn.customer, "customer_name") or "").strip()

# Last fallback only (avoid showing "Walk In Customer Address")
if not consignee_name:
    consignee_name = (addr.address_title or dn.customer or "").strip()

shipment.consignee_name = consignee_name

    shipment.city = addr.city
    shipment.address = compose_address(addr)
    shipment.phone = get_phone(addr, dn)

    if not shipment.city:
        frappe.throw("Destination city missing in Shipping Address")
    if not shipment.phone:
        frappe.throw("Consignee phone number missing")
    if not shipment.address:
        frappe.throw("Consignee address missing")

    shipment.payment_mode = settings.default_payment_mode or "COD"
    shipment.pieces = int(settings.default_pieces or 1)

    # ✅ GRAMS ONLY
    shipment.weight_grams = resolve_shipment_weight_grams(dn)

    shipment.declared_value = flt(dn.grand_total or 0)
    shipment.cod_amount = (
        shipment.declared_value
        if shipment.payment_mode == "COD"
        else 0
    )

    shipment.insert(ignore_permissions=True)
    return shipment


# =====================================================
# REMARKS (MANUAL OVERRIDE SUPPORTED)
# =====================================================

def build_remarks_for_leopards(dn, max_length=250):
    override = (dn.get("custom_leopards_remarks_override") or "").strip()
    if override:
        return override[:max_length]

    parts = []
    for item in dn.items:
        if item.item_name:
            parts.append(f"{item.item_name} x{int(item.qty or 1)}")

    remarks = ", ".join(parts)

    if dn.name:
        remarks = f"{remarks} | DN: {dn.name}" if remarks else f"DN: {dn.name}"

    return remarks[:max_length] if remarks else "N/A"


# =====================================================
# BUILD API PAYLOAD (FINAL)
# =====================================================

def build_book_packet_payload(shipment):
    settings = get_leopards_settings()

    if not settings.default_origin_city:
        frappe.throw("Default Origin City is required in Leopards Settings")

    origin_city_id = resolve_leopards_city_id(
        settings.default_origin_city, for_origin=True
    )
    destination_city_id = resolve_leopards_city_id(
        shipment.city, for_origin=False
    )

    weight_grams = int(shipment.weight_grams or 0)
    if weight_grams <= 0 or weight_grams > 100000:
        frappe.throw(
            f"Invalid weight {weight_grams}g. Leopards allows 1–100000 grams."
        )

    dn = frappe.get_doc("Delivery Note", shipment.delivery_note)

    payload = {
        "booked_packet_order_id": shipment.delivery_note,
        "booked_packet_weight": weight_grams,
        "booked_packet_no_piece": int(shipment.pieces),
        "booked_packet_collect_amount": int(shipment.cod_amount or 0),

        "origin_city": origin_city_id,
        "destination_city": destination_city_id,

        "shipment_type": shipment.service_type or settings.default_service_type or "Overnight",
        "product_type": shipment.product_type or settings.default_product_type or "Parcel",
        "shipment_mode": shipment.shipment_mode or settings.shipment_mode or "Domestic",

        "order_payment_method": shipment.payment_mode,

        "shipment_name_eng": settings.shipper_name or shipment.company,
        "shipment_phone": settings.shipper_phone,
        "shipment_address": settings.shipper_address,

        "consignment_name_eng": shipment.consignee_name,
        "consignment_phone": shipment.phone,
        "consignment_address": shipment.address,

        "special_instructions": build_remarks_for_leopards(dn),
    }

    shipment.request_payload = json.dumps(payload, indent=2)
    shipment.save(ignore_permissions=True)

    return payload