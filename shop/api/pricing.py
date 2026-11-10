"""Rates staff set in the Shop admin, kept as ERPNext Pricing Rules: percent off, or a fixed price,
for an Item Group or a product, with quantity breaks, for every trade account, one customer, or
everyone.

One rule applies to a line, the most specific: a customer's own over the trade accounts', theirs
over everyone's; within each, a product's over its Item Group's and an inner Item Group's over an
outer one's. ERPNext picks it by priority, which is set here on every rule of this shape (one Item
Group or product, a percentage or a rate, for one of those parties); the quantity breaks of one
target are given ranges that don't overlap. Rules set up any other way are left as they are."""

import frappe
from frappe import _
from frappe.utils import cint, cstr, flt, fmt_money

from shop.api import only_managers
from shop.api.trade import trade_group

DISCOUNT, PRICE = "discount", "price"
ITEM_GROUP, PRODUCT = "Item Group", "Product"
# priority bands: everyone 1-6, trade accounts 7-12, a customer 13-18; within a band an Item Group
# by its depth (5 and deeper alike), a product above any Item Group
SCOPE_BASE = {"everyone": 0, "trade": 6, "customer": 12}
DEEPEST = 5
# a quantity break's range ends just before the next one starts
QTY_STEP = 0.001
RULE_FIELDS = [
	"name",
	"title",
	"apply_on",
	"applicable_for",
	"customer",
	"customer_group",
	"rate_or_discount",
	"discount_percentage",
	"rate",
	"currency",
	"min_qty",
	"max_qty",
	"company",
	"mixed_conditions",
	"is_cumulative",
	"apply_rule_on_other",
	"for_price_list",
	"margin_rate_or_amount",
	"condition",
	"valid_from",
	"valid_upto",
]


def store_company() -> str:
	return frappe.get_cached_doc("Shop Settings").company


def company_currency() -> str:
	return frappe.get_cached_value("Company", store_company(), "default_currency")


def party(scope: str, customer: str | None = None) -> dict:
	"""The Pricing Rule fields naming who a scope's rates are for."""
	if scope == "everyone":
		return {"applicable_for": "", "customer": None, "customer_group": None}
	if scope == "trade":
		group = trade_group()
		if not group:
			frappe.throw(_("Choose the trade customer group in Settings first"))
		return {"applicable_for": "Customer Group", "customer": None, "customer_group": group}
	if scope == "customer":
		if not customer or not frappe.db.exists("Customer", customer):
			frappe.throw(_("Choose a customer"))
		return {"applicable_for": "Customer", "customer": customer, "customer_group": None}
	frappe.throw(_("Unknown rates {0}").format(scope))


def scope_of(rule) -> tuple[str, str | None] | None:
	"""Whose rates a rule is: ("everyone", None), ("trade", None) or ("customer", name)."""
	if not rule.applicable_for:
		return ("everyone", None)
	if (
		rule.applicable_for == "Customer Group"
		and rule.customer_group
		and rule.customer_group == trade_group()
	):
		return ("trade", None)
	if rule.applicable_for == "Customer" and rule.customer:
		return ("customer", rule.customer)
	return None


def selling_rules(filters: dict | None = None) -> list[frappe._dict]:
	"""Selling price rules on an Item Group or a product, with what each applies to."""
	rules = frappe.get_all(
		"Pricing Rule",
		filters={
			"selling": 1,
			"disable": 0,
			"price_or_product_discount": "Price",
			"coupon_code_based": 0,
			"apply_on": ["in", ["Item Code", "Item Group"]],
			**(filters or {}),
		},
		# a rule past its end date no longer prices anything
		or_filters=[["valid_upto", "is", "not set"], ["valid_upto", ">=", frappe.utils.nowdate()]],
		fields=RULE_FIELDS,
	)
	names = [rule.name for rule in rules] or [""]
	targets: dict[str, list] = {}
	for doctype, field in (
		("Pricing Rule Item Code", "item_code"),
		("Pricing Rule Item Group", "item_group"),
	):
		for row in frappe.get_all(
			doctype, filters={"parent": ["in", names], "parenttype": "Pricing Rule"}, fields=["parent", field]
		):
			targets.setdefault(row.parent, []).append(row[field])
	for rule in rules:
		rule.targets = targets.get(rule.name, [])
		rule.target_type = PRODUCT if rule.apply_on == "Item Code" else ITEM_GROUP
	return rules


def is_simple(rule) -> bool:
	"""A rule of the shape the Shop admin sets: one target, a percentage or a rate, for one party,
	and no other conditions."""
	return (
		len(rule.targets) == 1
		and rule.rate_or_discount in ("Discount Percentage", "Rate")
		and not (rule.mixed_conditions or rule.is_cumulative or rule.apply_rule_on_other)
		and not (rule.for_price_list or flt(rule.margin_rate_or_amount) or rule.condition)
		and rule.company in (None, "", store_company())
		and scope_of(rule) is not None
	)


def managed_rules(filters: dict | None = None) -> list[frappe._dict]:
	return [rule for rule in selling_rules(filters) if is_simple(rule)]


def item_group_depths() -> dict[str, int]:
	"""How deep each Item Group sits: the root is 1."""
	groups = frappe.get_all("Item Group", fields=["name", "lft", "rgt"], order_by="lft")
	depths, open_groups = {}, []
	for group in groups:
		while open_groups and open_groups[-1] < group.rgt:
			open_groups.pop()
		depths[group.name] = len(open_groups) + 1
		open_groups.append(group.rgt)
	return depths


def priority(rule, depths: dict[str, int]) -> int:
	scope = scope_of(rule)[0]
	specific = DEEPEST + 1 if rule.target_type == PRODUCT else min(depths.get(rule.targets[0], 1), DEEPEST)
	return SCOPE_BASE[scope] + specific


def arrange() -> None:
	"""Give every rule of the Shop admin's shape its priority, and each target's quantity breaks
	ranges that don't overlap."""
	depths = item_group_depths()
	tiers: dict[tuple, list] = {}
	for rule in managed_rules():
		tiers.setdefault((scope_of(rule), rule.target_type, rule.targets[0]), []).append(rule)
	for rules in tiers.values():
		rules.sort(key=lambda rule: flt(rule.min_qty))
		for index, rule in enumerate(rules):
			following = rules[index + 1] if index + 1 < len(rules) else None
			wanted = (1, str(priority(rule, depths)), flt(following.min_qty) - QTY_STEP if following else 0)
			current = frappe.db.get_value(
				"Pricing Rule", rule.name, ["has_priority", "priority", "max_qty"], as_dict=True
			)
			if (cint(current.has_priority), cstr(current.priority), flt(current.max_qty)) != wanted:
				frappe.db.set_value(
					"Pricing Rule",
					rule.name,
					{"has_priority": wanted[0], "priority": wanted[1], "max_qty": wanted[2]},
				)
	from shop.storefront.pricing import forget_rates

	forget_rates()


def describe(rule) -> dict:
	currency = rule.currency or company_currency()
	if rule.rate_or_discount == "Rate":
		kind, value, label = PRICE, flt(rule.rate), fmt_money(rule.rate, currency=currency)
	else:
		kind, value = DISCOUNT, flt(rule.discount_percentage)
		label = _("{0}% off").format(f"{value:g}")
	return {
		"name": rule.name,
		"kind": kind,
		"value": value,
		"label": label,
		"from_qty": flt(rule.min_qty),
		"valid_upto": rule.valid_upto,
	}


def target_label(target_type: str, target: str) -> str:
	if target_type == ITEM_GROUP:
		return target
	return (
		frappe.db.get_value("Shop Product", {"item": target}, "product_name")
		or frappe.get_cached_value("Item", target, "item_name")
		or target
	)


def grouped(rules: list) -> list[dict]:
	"""Rules by what they apply to, each with its quantity breaks in order."""
	targets: dict[tuple, dict] = {}
	for rule in sorted(rules, key=lambda rule: flt(rule.min_qty)):
		key = (rule.target_type, rule.targets[0])
		entry = targets.setdefault(
			key,
			{
				"target_type": key[0],
				"target": key[1],
				"label": target_label(*key),
				"tiers": [],
			},
		)
		entry["tiers"].append(describe(rule))
	return sorted(targets.values(), key=lambda entry: (entry["target_type"] != ITEM_GROUP, entry["label"]))


def scope_rules(scope: str, customer: str | None = None) -> list:
	fields = party(scope, customer)
	filters = {"applicable_for": fields["applicable_for"] or ["is", "not set"]}
	if scope == "trade":
		filters["customer_group"] = fields["customer_group"]
	if scope == "customer":
		filters["customer"] = customer
	return selling_rules(filters)


@frappe.whitelist()
def get_rates(scope: str, customer: str | None = None, item: str | None = None) -> dict:
	"""A scope's rates by what they apply to, and how many of its rules are set up in Desk in some
	other way. item narrows it to one product."""
	only_managers()
	rules = scope_rules(scope, customer)
	simple = [rule for rule in rules if is_simple(rule)]
	if item:
		simple = [rule for rule in simple if rule.target_type == PRODUCT and rule.targets[0] == item]
	return {
		"rates": grouped(simple),
		"set_in_desk": 0 if item else len(rules) - len(simple),
		"currency": company_currency(),
		"item_groups": [{"name": name, "depth": depth} for name, depth in item_group_depths().items()],
	}


def check_target(target_type: str, target: str) -> None:
	if target_type == ITEM_GROUP and frappe.db.exists("Item Group", target):
		return
	if target_type == PRODUCT and frappe.db.exists("Item", {"name": target, "disabled": 0}):
		return
	frappe.throw(_("Choose an Item Group or a product"))


def clean_tiers(tiers: list[dict]) -> list[frappe._dict]:
	"""Quantity breaks as given: from what quantity (1 is any), percent off or a price."""
	if not tiers:
		frappe.throw(_("Add a rate"))
	cleaned, starts = [], set()
	for tier in tiers:
		tier = frappe._dict(tier)
		start = flt(tier.from_qty) if flt(tier.from_qty) > 1 else 0
		if start in starts:
			frappe.throw(_("Two rates start at the same quantity"))
		starts.add(start)
		value = flt(tier.value)
		if tier.kind == DISCOUNT and not 0 < value <= 100:
			frappe.throw(_("A discount is a percentage between 0 and 100"))
		if tier.kind == PRICE and value <= 0:
			frappe.throw(_("A price must be more than nothing"))
		if tier.kind not in (DISCOUNT, PRICE):
			frappe.throw(_("Choose percent off or a price"))
		cleaned.append(frappe._dict(min_qty=start, kind=tier.kind, value=value))
	return sorted(cleaned, key=lambda tier: tier.min_qty)


@frappe.whitelist(methods=["POST"])
def save_rates(
	scope: str, target_type: str, target: str, tiers: list[dict], customer: str | None = None
) -> dict:
	"""Set a scope's rates for an Item Group or a product: its quantity breaks, the first of which
	may apply to any quantity. Breaks no longer given are removed."""
	only_managers()
	fields = party(scope, customer)
	check_target(target_type, target)
	wanted = clean_tiers(tiers)
	existing = {
		flt(rule.min_qty): rule
		for rule in scope_rules(scope, customer)
		if is_simple(rule) and rule.target_type == target_type and rule.targets[0] == target
	}
	label = target_label(target_type, target)
	who = {"everyone": _("Everyone"), "trade": _("Trade"), "customer": customer}[scope]
	for tier in wanted:
		rule = existing.pop(tier.min_qty, None)
		doc = frappe.get_doc("Pricing Rule", rule.name) if rule else frappe.new_doc("Pricing Rule")
		title = f"{who}: {label}" + (
			f" ({_('from {0}').format(f'{tier.min_qty:g}')})" if tier.min_qty else ""
		)
		doc.update(
			{
				"title": title[:140],
				"apply_on": "Item Code" if target_type == PRODUCT else "Item Group",
				"selling": 1,
				"company": store_company(),
				"currency": company_currency(),
				"min_qty": tier.min_qty,
				"max_qty": 0,
				"rate_or_discount": "Rate" if tier.kind == PRICE else "Discount Percentage",
				"rate": tier.value if tier.kind == PRICE else 0,
				"discount_percentage": tier.value if tier.kind == DISCOUNT else 0,
				**fields,
			}
		)
		if doc.is_new():
			if target_type == PRODUCT:
				doc.append("items", {"item_code": target})
			else:
				doc.append("item_groups", {"item_group": target})
		doc.save(ignore_permissions=True)
	for rule in existing.values():
		retire(rule.name)
	arrange()
	return get_rates(scope, customer)


@frappe.whitelist(methods=["POST"])
def remove_rates(scope: str, target_type: str, target: str, customer: str | None = None) -> dict:
	"""Remove a scope's rates for an Item Group or a product."""
	only_managers()
	party(scope, customer)
	for rule in scope_rules(scope, customer):
		if is_simple(rule) and rule.target_type == target_type and rule.targets[0] == target:
			retire(rule.name)
	arrange()
	return get_rates(scope, customer)


def retire(name: str) -> None:
	"""Remove a rule; one that carts or orders were priced with stays, turned off, as their record."""
	frappe.db.savepoint("retire_rule")
	try:
		frappe.delete_doc("Pricing Rule", name, ignore_permissions=True)
	except frappe.LinkExistsError:
		frappe.db.rollback(save_point="retire_rule")
		frappe.clear_messages()
		frappe.db.set_value("Pricing Rule", name, "disable", 1)
		from shop.storefront.pricing import forget_rates

		forget_rates()
