// Store quotes: email the customer a link to view and accept the quotation online.
frappe.ui.form.on("Quotation", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1 || !frm.doc.contact_email || ["Ordered", "Lost"].includes(frm.doc.status)) return;
		frm.add_custom_button(__("Email Quote to Customer"), () =>
			frappe.call({
				method: "shop.storefront.quotes.send_quote",
				args: { name: frm.doc.name },
				freeze: true,
				callback: (r) => {
					frappe.show_alert({ message: __("Quote emailed to {0}", [frm.doc.contact_email]), indicator: "green" });
					frm.reload_doc();
				},
			})
		);
	},
});
