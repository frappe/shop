"""The store's emails are Frappe Email Templates, so they can be edited in the desk.

Each template is made with the wording below. A template staff haven't edited follows that wording
when it changes; an edited one is never overwritten. It is rendered with
`doc` (the order, quotation or lead), `store_name` and the pieces each email needs, already
formatted (`lines_html`, `payment_html`, `order_url`...). Subjects are plain text; bodies escape
what shoppers typed. A failed email is logged and never stops the action that sends it.
"""

import frappe
from frappe import _lt
from frappe.model.document import Document

ORDER = "Sales Order"
QUOTATION = "Quotation"
LEAD = "Lead"

# the default wording last written to each template
DEFAULTS_KEY = "shop_email_template_defaults"

# key: (Email Template name, reference doctype, subject, body)
TEMPLATES = {
	"order_confirmed": (
		"Shop: Order Confirmed",
		ORDER,
		_lt("Your order {{ doc.name }} is confirmed"),
		_lt(
			"<p>Thank you for your order at {{ store_name }}.</p>"
			"<p>Order: <b>{{ doc.name }}</b></p>{{ lines_html }}{{ payment_html }}"
			'<p><a href="{{ order_url }}">View your order</a></p>{{ terms_html }}'
		),
	),
	"order_payment_instructions": (
		"Shop: Order Payment Instructions",
		ORDER,
		_lt("Your order {{ doc.name }}: how to pay"),
		_lt(
			"<p>Thank you for your order at {{ store_name }}.</p>"
			"<p>Order: <b>{{ doc.name }}</b></p>{{ lines_html }}{{ payment_html }}"
			'<p><a href="{{ order_url }}">View your order</a></p>{{ terms_html }}'
		),
	),
	"payment_reminder": (
		"Shop: Order Payment Reminder",
		ORDER,
		_lt("Your order {{ doc.name }} is waiting for payment"),
		_lt(
			"<p>Your order {{ doc.name }} at {{ store_name }} hasn't been paid yet.</p>{{ lines_html }}"
			'<p><a href="{{ pay_url }}">Pay now</a></p>'
			"{% if due_date %}<p>Unpaid orders are cancelled after {{ due_date }}.</p>{% endif %}"
			'<p><a href="{{ order_url }}">View your order</a></p>'
		),
	),
	"payment_received": (
		"Shop: Payment Received",
		ORDER,
		_lt("Payment received for order {{ doc.name }}"),
		_lt(
			"<p>Thank you, we've received your payment for order {{ doc.name }}."
			"{% if shipping_emails %} We'll let you know when it ships.{% endif %}</p>"
			"{% if invoice %}<p>Your invoice {{ invoice }} is attached.</p>{% endif %}"
		),
	),
	"payment_short": (
		"Shop: Payment Part Received",
		ORDER,
		_lt("Part payment received for order {{ doc.name }}"),
		_lt(
			"<p>Thank you, we've received {{ received }} for order {{ doc.name }}. {{ owed }} is still owed.</p>"
			"<p>Banks along the way sometimes take a fee from a transfer. Please send the rest with the same "
			"reference, and we'll send your order once it is paid in full.</p>"
			"{{ payment_html }}"
		),
	),
	"return_requested": (
		"Shop: Return Requested",
		ORDER,
		_lt("We've received your request for order {{ doc.name }}"),
		_lt(
			"<p>We've received your {{ request_type|lower }} request for {{ qty }} \u00d7 {{ item_name }} from order "
			"{{ doc.name }}. We'll reply once we've looked at it.</p>"
		),
	),
	"return_staff": (
		"Shop: Return Requested (Staff)",
		ORDER,
		_lt("{{ request_type }} requested for order {{ doc.name }}"),
		_lt(
			"<p>{{ doc.customer_name | e }} asked for a {{ request_type|lower }} of {{ qty }} \u00d7 {{ item_name | e }} "
			"from order {{ doc.name }}.</p><p>Reason: {{ reason | e }}</p><p>Review it in the store admin under Returns.</p>"
		),
	),
	"return_approved": (
		"Shop: Return Approved",
		ORDER,
		_lt("Your {{ request_type|lower }} for order {{ doc.name }} is approved"),
		_lt(
			"<p>We've approved your {{ request_type|lower }} of {{ qty }} \u00d7 {{ item_name }} from order {{ doc.name }}.</p>"
			"{% if note %}<p>{{ note }}</p>{% endif %}"
			"<p>Please send the item back with your order number, {{ doc.name }}. Reply to this email if you need our "
			"return address.</p>"
		),
	),
	"return_rejected": (
		"Shop: Return Declined",
		ORDER,
		_lt("Your {{ request_type|lower }} request for order {{ doc.name }}"),
		_lt(
			"<p>We're sorry, we can't accept the {{ request_type|lower }} of {{ item_name }} from order {{ doc.name }}.</p>"
			"{% if note %}<p>{{ note }}</p>{% endif %}<p>Reply to this email if you'd like to talk about it.</p>"
		),
	),
	"return_completed": (
		"Shop: Return Completed",
		ORDER,
		_lt("Your {{ request_type|lower }} for order {{ doc.name }} is complete"),
		_lt(
			"<p>We've received {{ qty }} \u00d7 {{ item_name }} from order {{ doc.name }}.</p>"
			"{% if credit_note %}<p>Your credit note {{ credit_note }} for {{ amount }} is attached."
			"{% if refund_due %} We'll let you know when the refund is on its way."
			"{% else %} It is taken off what you owe.{% endif %}</p>{% endif %}"
			"{% if note %}<p>{{ note }}</p>{% endif %}"
		),
	),
	"order_cancelled_by_store": (
		"Shop: Order Cancelled By Store",
		ORDER,
		_lt("Your order {{ doc.name }} has been cancelled"),
		_lt(
			"<p>We've cancelled your order {{ doc.name }} at {{ store_name }}.</p>"
			"{% if note %}<p>{{ note }}</p>{% endif %}"
			"{% if credit_note %}<p>Your credit note {{ credit_note }} for {{ amount }} is attached."
			"{% if refund_due %} We'll let you know when the refund of what you paid is on its way."
			"{% else %} There's nothing to pay for this order.{% endif %}</p>{% endif %}"
			"<p>Reply to this email if you have any questions.</p>"
		),
	),
	"refund_sent": (
		"Shop: Refund Sent",
		ORDER,
		_lt("Your refund for order {{ doc.name }}"),
		_lt(
			"<p>We've refunded {{ amount }} for order {{ doc.name }}{% if to_card %} the way you paid"
			"{% if gateway %} ({{ gateway }}){% endif %}. It can take a few days to show on your statement"
			"{% else %} to your bank account{% endif %}.</p>"
		),
	),
	"order_cancelled": (
		"Shop: Order Cancelled",
		ORDER,
		_lt("Your order {{ doc.name }} has been cancelled"),
		_lt(
			"<p>We didn't receive payment for order {{ doc.name }} by {{ due_date }}, so it has been cancelled.</p>"
			"<p>If you still want the items, please place a new order at {{ store_name }}. If you have paid, reply to "
			"this email and we'll sort it out.</p>"
		),
	),
	"order_shipped": (
		"Shop: Order Shipped",
		ORDER,
		_lt("Your order {{ doc.name }} is on its way"),
		_lt(
			"<p>{% if partly %}Part of your order {{ doc.name }} has shipped. The rest follows in its own parcel."
			"{% else %}Good news: your order {{ doc.name }} has shipped.{% endif %}</p>"
			"{% if carrier_line %}<p>{{ carrier_line }}</p>{% endif %}"
			'{% if tracking_url %}<p><a href="{{ tracking_url }}">Track your parcel</a></p>{% endif %}'
			'<p><a href="{{ order_url }}">View your order</a></p>'
		),
	),
	"ready_for_pickup": (
		"Shop: Ready for Pickup",
		ORDER,
		_lt("Your order {{ doc.name }} is ready to collect"),
		_lt(
			"<p>Your order {{ doc.name }} is ready to collect{% if location %} from {{ location | e }}{% endif %}.</p>"
			"{% if instructions %}<p>{{ instructions | e }}</p>{% endif %}"
			'<p><a href="{{ order_url }}">View your order</a></p>'
		),
	),
	"order_delivered": (
		"Shop: Order Delivered",
		ORDER,
		_lt("Your order {{ doc.name }} has been delivered"),
		_lt(
			"<p>Your order {{ doc.name }} has been delivered. Thank you for shopping with us.</p>"
			'<p><a href="{{ order_url }}">View your order</a></p>'
		),
	),
	"quote_request_received": (
		"Shop: Quote Request Received",
		QUOTATION,
		_lt("We've received your quote request {{ doc.name }}"),
		_lt("<p>Thanks, we've received your request. We'll check it and email you the quote.</p>"),
	),
	"quote_request_staff": (
		"Shop: New Quote Request",
		QUOTATION,
		_lt("Quote request {{ doc.name }} from {{ customer_name }}"),
		_lt(
			"<p>{{ customer_name | e }} ({{ email | e }}) asked for a quote.</p><p>{{ message | e }}</p>"
			'<p><a href="{{ desk_url }}">Open the quotation</a></p>'
		),
	),
	"quote_changed_staff": (
		"Shop: Quote Prices Changed",
		QUOTATION,
		_lt("Quote {{ doc.name }} can't be accepted: prices have changed"),
		_lt('<p>{{ note | e }}</p><p><a href="{{ desk_url }}">Open the quotation</a></p>'),
	),
	"quote_ready": (
		"Shop: Quote Ready",
		QUOTATION,
		_lt("Your quote {{ doc.name }}"),
		_lt(
			"<p>Here is your quote. It's valid until {{ valid_till }}.</p>"
			'<p><a href="{{ quote_url }}">View and accept the quote</a></p>'
		),
	),
	"trade_application_received": (
		"Shop: Trade Application Received",
		LEAD,
		_lt("We've received your trade account application"),
		_lt(
			"<p>Thanks for applying for a {{ store_name }} trade account for {{ doc.company_name | e }}. We'll review it "
			"and email you.</p>"
		),
	),
	"trade_application_staff": (
		"Shop: New Trade Application",
		LEAD,
		_lt("Trade account application: {{ doc.company_name }}"),
		_lt(
			"<p>{{ doc.company_name | e }} ({{ (doc.country or '') | e }}) applied for a trade account.</p>"
			'<p><a href="{{ review_url }}">Review the application</a></p>'
		),
	),
	"trade_account_approved": (
		"Shop: Trade Account Approved",
		LEAD,
		_lt("Your {{ store_name }} trade account is ready"),
		_lt(
			"<p>Your trade account for {{ doc.company_name | e }} is approved. Sign in to see your trade prices"
			"{% if on_account %} and pay on account{% endif %}.</p>"
			'<p><a href="{{ sign_in_url }}">Sign in</a></p>'
		),
	),
	"trade_application_declined": (
		"Shop: Trade Application Declined",
		LEAD,
		_lt("Your {{ store_name }} trade account application"),
		_lt(
			"<p>Thank you for applying. We can't open a trade account for {{ doc.company_name | e }} at the moment.</p>"
			"{% if reason %}<p>{{ reason | e }}</p>{% endif %}<p>You can still buy at retail prices in the store.</p>"
		),
	),
	"back_in_stock": (
		"Shop: Back in Stock",
		"Shop Stock Alert",
		_lt("{{ item_name }} is back in stock at {{ store_name }}"),
		_lt(
			"<p>Good news: {{ item_name | e }} is back in stock at {{ store_name }}.</p>"
			'<p><a href="{{ product_url }}">See it in the store</a></p>'
			"<p>You asked us to tell you, so this is the only email about it.</p>"
		),
	),
	"cart_reminder": (
		"Shop: Cart Reminder",
		"Shop Cart",
		_lt("Your cart at {{ store_name }} is waiting"),
		_lt(
			"<p>You left these in your cart at {{ store_name }}. We've kept them for you.</p>{{ lines_html }}"
			'<p><a href="{{ cart_url }}">Return to your cart</a></p>'
		),
	),
}


def ensure_templates() -> None:
	"""Make any missing store Email Template with its default wording, and bring the ones staff
	haven't edited up to the current wording."""
	if not frappe.db.table_exists("Email Template"):
		return
	written = frappe.parse_json(frappe.db.get_global(DEFAULTS_KEY) or "{}")
	for name, reference_doctype, subject, body in TEMPLATES.values():
		# in the site's language when the template is made
		subject, body = str(subject), str(body)
		wording = fingerprint(subject, body)
		if frappe.db.exists("Email Template", name):
			doc = frappe.get_doc("Email Template", name)
			current = fingerprint(doc.subject, doc.response_html)
			# a template made before its wording was recorded is unedited if it was never saved again
			unedited = current == written.get(name) if name in written else doc.modified == doc.creation
			if not unedited:
				continue
			if current != wording:
				doc.subject = subject
				doc.response_html = body
				doc.save(ignore_permissions=True)
		else:
			doc = frappe.new_doc("Email Template")
			doc.update(
				{
					"__newname": name,
					"subject": subject,
					"use_html": 1,
					"response_html": body,
					"reference_doctype": reference_doctype
					if frappe.db.exists("DocType", reference_doctype)
					else None,
				}
			)
			doc.insert(ignore_permissions=True)
		written[name] = wording
	frappe.db.set_global(DEFAULTS_KEY, frappe.as_json(written))


def fingerprint(subject: str | None, body: str | None) -> str:
	from hashlib import sha256

	return sha256(f"{subject or ''}\0{body or ''}".encode()).hexdigest()


def render(key: str, doc, **context) -> tuple[str, str]:
	"""The subject and body of a store email for this document."""
	name = TEMPLATES[key][0]
	if not frappe.db.exists("Email Template", name):
		ensure_templates()
	template = frappe.get_doc("Email Template", name)
	settings = frappe.get_cached_doc("Shop Settings")
	args = {
		"doc": doc.as_dict() if isinstance(doc, Document) else doc,
		"store_name": settings.store_name
		or frappe.get_cached_value("Company", settings.company, "company_name"),
		**context,
	}
	return template.get_formatted_subject(args), template.get_formatted_response(args)


def send(key: str, recipients, doc, attachments: list | None = None, **context) -> None:
	"""Send a store email to `recipients`, linked to `doc`; a failure is logged, never raised."""
	recipients = [r for r in (recipients if isinstance(recipients, list) else [recipients]) if r]
	if not recipients:
		return
	try:
		subject, message = render(key, doc, **context)
		frappe.sendmail(
			recipients=recipients,
			subject=subject,
			message=message,
			attachments=attachments or [],
			reference_doctype=doc.doctype,
			reference_name=doc.name,
		)
	except Exception:
		frappe.log_error(title=f"Store email failed: {key}")
