// Trade account applications from the store are Leads with UTM Source "Store Trade Application".
frappe.ui.form.on("Lead", {
	refresh(frm) {
		const from_store = frm.doc.utm_source === "Store Trade Application";
		if (frm.is_new() || !from_store || frm.doc.status === "Converted" || frm.doc.qualification_status === "Unqualified") return;
		frm.add_custom_button(__("Approve Trade Account"), () => approve(frm), __("Trade Account"));
		frm.add_custom_button(__("Decline"), () => decline(frm), __("Trade Account"));
	},
});

async function approve(frm) {
	const defaults = (await frappe.xcall("shop.storefront.accounts.trade_defaults", { lead: frm.doc.name })) || {};
	const dialog = new frappe.ui.Dialog({
		title: __("Approve Trade Account for {0}", [frappe.utils.escape_html(frm.doc.company_name || frm.doc.lead_name)]),
		fields: [
			{
				fieldtype: "HTML",
				options: defaults.existing_customer
					? `<p class="text-muted">${__("The applicant's customer {0} becomes a trade account. Fields left empty keep its current values.", [frappe.utils.escape_html(defaults.existing_customer)])}</p>`
					: `<p class="text-muted">${__("A new Customer is made from this Lead.")}</p>`,
			},
			{ fieldname: "customer_group", fieldtype: "Link", options: "Customer Group", label: __("Customer Group"), reqd: 1, default: defaults.customer_group },
			{ fieldname: "payment_terms", fieldtype: "Link", options: "Payment Terms Template", label: __("Payment Terms"), default: defaults.payment_terms },
			{ fieldname: "allow_on_account", fieldtype: "Check", label: __("Pay on Account at the Store") },
			{ fieldname: "credit_limit", fieldtype: "Currency", label: __("Credit Limit") },
			{ fieldname: "price_list", fieldtype: "Link", options: "Price List", label: __("Price List"),
			  description: __("Optional. Usually leave empty: the Customer Group's Price List and Pricing Rules apply."),
			  get_query: () => ({ filters: { selling: 1, enabled: 1 } }) },
		],
		primary_action_label: __("Approve"),
		primary_action(values) {
			frappe.call({
				method: "shop.storefront.accounts.approve_trade",
				args: { lead: frm.doc.name, ...values },
				freeze: true,
				freeze_message: __("Approving"),
				callback: (r) => {
					dialog.hide();
					frm.reload_doc();
					frappe.show_alert({ message: __("Trade account approved: {0}", [frappe.utils.escape_html(r.message.customer)]), indicator: "green" });
				},
			});
		},
	});
	dialog.show();
}

function decline(frm) {
	frappe.prompt(
		{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason (sent to the applicant)") },
		(values) =>
			frappe.call({
				method: "shop.storefront.accounts.decline_trade",
				args: { lead: frm.doc.name, reason: values.reason },
				callback: () => frm.reload_doc(),
			}),
		__("Decline Application"),
		__("Decline")
	);
}
