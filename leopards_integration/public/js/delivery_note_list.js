frappe.listview_settings["Delivery Note"] = {
    refresh(listview) {
        // Remove existing to avoid duplicates
        listview.page.clear_menu();

        listview.page.add_menu_item(
            __("Bulk Book Leopards"),
            () => {
                const selected = listview.get_checked_items();

                if (!selected || !selected.length) {
                    frappe.msgprint(__("Please select Delivery Notes first."));
                    return;
                }

                const dn_names = selected.map(d => d.name);

                frappe.call({
                    method: "leopards_integration.api.bulk_booking.bulk_book_delivery_notes",
                    args: {
                        delivery_notes: dn_names
                    },
                    freeze: true,
                    freeze_message: __("Booking Leopards…"),
                    callback: (r) => {
                        const res = r.message || {};
                        const booked = res.booked || [];
                        const skipped = res.skipped || [];
                        const failed = res.failed || [];

                        let html = "";

                        if (booked.length) {
                            html += "<h4>Booked</h4><ul>" +
                                booked.map(x => `<li>${x.dn} → ${x.cn || ""}</li>`).join("") +
                                "</ul>";
                        }

                        if (skipped.length) {
                            html += "<h4>Skipped</h4><ul>" +
                                skipped.map(x => `<li>${x.dn} (${x.reason})</li>`).join("") +
                                "</ul>";
                        }

                        if (failed.length) {
                            html += "<h4>Failed</h4><ul>" +
                                failed.map(x => `<li>${x.dn}: ${x.error}</li>`).join("") +
                                "</ul>";
                        }

                        frappe.msgprint({
                            title: __("Leopards Bulk Booking Result"),
                            message: html || __("No results."),
                            indicator: failed.length ? "red" : "green",
                            wide: true
                        });

                        listview.refresh();
                    }
                });
            }
        );
    }
};
