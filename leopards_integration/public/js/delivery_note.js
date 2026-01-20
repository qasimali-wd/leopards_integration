frappe.ui.form.on("Delivery Note", {
  refresh(frm) {
    const is_submitted = frm.doc.docstatus === 1;
    const already_booked = !!frm.doc.custom_leopards_cn_number;
    const status = frm.doc.custom_leopards_booking_status || "";

    if (!is_submitted) return;

    // Show if not booked yet OR failed (allow retry)
    if (!already_booked || status === "Failed") {
      frm.add_custom_button(__("Book with Leopards"), () => {
        frappe.call({
          method: "leopards_integration.api.booking.book_from_delivery_note",
          args: { delivery_note: frm.doc.name },
          freeze: true,
          freeze_message: __("Booking shipment with Leopards..."),
        }).then((r) => {
          if (r && r.message) {
            frappe.msgprint({
              title: __("Booked"),
              message: __("CN Number: {0}", [r.message.cn_number]),
              indicator: "green",
            });
            frm.reload_doc();
          }
        });
      }, __("Leopards"));
    }

    // Quick open slip link (if available)
    if (frm.doc.custom_leopards_slip_link) {
      frm.add_custom_button(__("Open Slip"), () => {
        window.open(frm.doc.custom_leopards_slip_link, "_blank");
      }, __("Leopards"));
    }
  },
});

