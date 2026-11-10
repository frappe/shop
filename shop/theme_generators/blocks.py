"""Helpers for generating Builder Page block trees programmatically."""

import frappe


def block(
	element: str = "div",
	styles: dict | None = None,
	mobile: dict | None = None,
	tablet: dict | None = None,
	children: list | None = None,
	name: str | None = None,
	text: str | None = None,
	attrs: dict | None = None,
	classes: list | None = None,
	**extra,
) -> dict:
	node = {
		"blockId": frappe.generate_hash(length=10),
		"element": element,
		"attributes": attrs or {},
		"customAttributes": {},
		"classes": classes or [],
		"baseStyles": styles or {},
		"mobileStyles": mobile or {},
		"tabletStyles": tablet or {},
		"children": children or [],
	}
	if name:
		node["blockName"] = name
	if text is not None:
		node["innerHTML"] = text
	node.update(extra)
	return node


def root(styles: dict, children: list) -> dict:
	node = block("div", styles=styles, children=children, name="Root")
	node["originalElement"] = "body"
	return node


def dv(key: str, prop: str, kind: str = "key") -> dict:
	return {"comesFrom": "dataScript", "key": key, "property": prop, "type": kind}


def repeater(key: str, child: dict, styles: dict, element: str = "div", **kwargs) -> dict:
	return block(
		element,
		styles=styles,
		children=[child],
		isRepeaterBlock=True,
		dataKey={"key": key, "comesFrom": "dataScript"},
		**kwargs,
	)


# client scripts the generator changed; Builder exports a script's file with the pages using it
changed_scripts = set()


def save_if_changed(doc, values: dict, force: bool = False) -> bool:
	"""Save the record only when the generator changed it: Builder writes a template's file on every
	save, so saving one that is the same would change its file for nothing."""
	before = None if doc.is_new() else content(doc)
	doc.update(values)
	if not force and before is not None and content(doc) == before:
		return False
	doc.save(ignore_permissions=True)
	return True


def content(doc) -> str:
	"""What a record holds, leaving out how Frappe tracks it (names, dates, rows not yet saved)."""

	def plain(value):
		if isinstance(value, dict):
			return {key: plain(item) for key, item in value.items() if not key.startswith("__")}
		if isinstance(value, list):
			return [plain(item) for item in value]
		return value

	return frappe.as_json(plain(doc.as_dict(no_default_fields=True)))


def stable_ids(blocks, owner: str):
	"""Give every block an id from what it belongs to and where it sits, so generating a theme again
	changes only what changed. A page places a component by pointing at its blocks' ids, so a page and
	its components stay in step however often they are generated."""
	from hashlib import sha1

	def assign(block: dict, path: str):
		block["blockId"] = sha1(f"{owner}/{path}".encode()).hexdigest()[:10]
		for index, child in enumerate(block.get("children") or []):
			assign(child, f"{path}.{index}")

	for index, block in enumerate(blocks if isinstance(blocks, list) else [blocks]):
		assign(block, str(index))
	return blocks


def upsert_component(component_id: str, component_name: str, block: dict) -> str:
	stable_ids(block, f"component:{component_id}")
	existing = frappe.db.exists("Builder Component", component_id)
	doc = (
		frappe.get_doc("Builder Component", component_id) if existing else frappe.new_doc("Builder Component")
	)
	save_if_changed(
		doc, {"component_id": component_id, "component_name": component_name, "block": frappe.as_json(block)}
	)
	return doc.name


def component_ref(component_id: str) -> dict:
	"""Block that renders a registered Builder Component, mirroring its children
	the way the editor does so overrides can attach per child."""
	source = frappe.parse_json(frappe.get_doc("Builder Component", component_id).block or "{}")
	return {
		"blockId": frappe.generate_hash(length=10),
		"extendedFromComponent": component_id,
		"children": [component_child_ref(child, component_id) for child in source.get("children") or []],
	}


def component_child_ref(source: dict, component_id: str) -> dict:
	return {
		"blockId": frappe.generate_hash(length=10),
		"isChildOfComponent": component_id,
		"referenceBlockId": source.get("blockId"),
		"children": [component_child_ref(child, component_id) for child in source.get("children") or []],
	}


def upsert_page(
	group: str,
	page_name: str,
	page_title: str,
	route: str,
	blocks: list,
	data_script: str,
	client_scripts: list[str] | None = None,
	authenticated_access: bool = False,
	meta_description: str | None = None,
):
	stable_ids(blocks, f"page:{group}:{route}")
	existing = frappe.db.exists("Builder Page", {"template_group": group, "is_template": 1, "route": route})
	page = frappe.get_doc("Builder Page", existing) if existing else frappe.new_doc("Builder Page")
	values = {
		"page_title": page_title,
		"route": route,
		"is_template": 1,
		"template_group": group,
		"published": 0,
		"blocks": frappe.as_json(blocks),
		"draft_blocks": None,
		"page_data_script": data_script,
		"body_html": '<script src="/assets/shop/js/storefront.js" defer></script>',
		"authenticated_access": 1 if authenticated_access else 0,
		"disable_indexing": 1 if private_route(route) else 0,
		"meta_description": meta_description,
		"client_scripts": [{"builder_script": script} for script in client_scripts or []],
	}
	if page.is_new():
		values["page_name"] = page_name
	save_if_changed(page, values, force=bool(changed_scripts & set(client_scripts or [])))
	return page


def private_route(route: str) -> bool:
	"""A shopper's own pages, which search engines leave out (Builder marks them noindex and keeps
	them out of its sitemap)."""
	return route in ("cart", "checkout") or route.startswith(("account/", "order-confirmation/", "quote/"))


def variable_doctype() -> tuple[str, str]:
	"""Builder renamed Builder Token to Builder Variable; support both (Builder v1.36 has Tokens)."""
	if frappe.db.exists("DocType", "Builder Variable"):
		return "Builder Variable", "variable_name"
	return "Builder Token", "token_name"


def upsert_variables(group: str, palette: dict[str, tuple[str, str | None]]) -> dict[str, str]:
	"""palette: {variable_name: (value, dark_value)} -> {variable_name: css var() reference}"""
	doctype, name_field = variable_doctype()
	refs = {}
	for variable_name, (value, dark_value) in palette.items():
		name = frappe.db.exists(doctype, {name_field: variable_name, "group": group})
		if name:
			doc = frappe.get_doc(doctype, name)
		else:
			doc = frappe.new_doc(doctype)
			doc.set(name_field, variable_name)
		doc.type = "Color"
		doc.value = value
		doc.dark_value = dark_value
		doc.group = group
		doc.save(ignore_permissions=True) if name else doc.insert(ignore_permissions=True)
		refs[variable_name] = f"var(--{doc.name}, {value})"
	return refs


def upsert_client_script(name: str, script_type: str, script: str) -> str:
	existing = frappe.db.exists("Builder Client Script", {"name": name})
	doc = (
		frappe.get_doc("Builder Client Script", existing)
		if existing
		else frappe.new_doc("Builder Client Script")
	)
	if existing:
		if save_if_changed(doc, {"script_type": script_type, "script": script}):
			changed_scripts.add(doc.name)
	else:
		doc.update({"script_type": script_type, "script": script, "name": name})
		doc.insert(ignore_permissions=True, set_name=name)
	return doc.name


def data_script(fn: str, expose: tuple = ()) -> str:
	"""A page's data script: the result of shop.storefront.page_data.<fn>, with `expose` keys also
	passed to the page's client scripts as page_data."""
	lines = [f'result = frappe.call("shop.storefront.page_data.{fn}")', "data.update(result)"]
	if expose:
		exposed = ", ".join(f'"{key}": result.get("{key}")' for key in expose)
		lines.append(f"data.page_data = {{{exposed}}}")
	return "\n".join(lines)
