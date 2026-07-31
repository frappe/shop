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


def upsert_component(component_id: str, component_name: str, block: dict) -> str:
	existing = frappe.db.exists("Builder Component", component_id)
	doc = frappe.get_doc("Builder Component", component_id) if existing else frappe.new_doc("Builder Component")
	doc.component_id = component_id
	doc.component_name = component_name
	doc.block = frappe.as_json(block)
	doc.save(ignore_permissions=True) if existing else doc.insert(ignore_permissions=True)
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
	existing = frappe.db.exists(
		"Builder Page", {"template_group": group, "is_template": 1, "route": route}
	)
	page = frappe.get_doc("Builder Page", existing) if existing else frappe.new_doc("Builder Page")
	page.update(
		{
			"page_name": page_name,
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
			"meta_description": meta_description,
			"client_scripts": [],
		}
	)
	for script in client_scripts or []:
		page.append("client_scripts", {"builder_script": script})
	page.save(ignore_permissions=True) if existing else page.insert(ignore_permissions=True)
	return page


def upsert_variables(group: str, palette: dict[str, tuple[str, str | None]]) -> dict[str, str]:
	"""palette: {variable_name: (value, dark_value)} -> {variable_name: css var() reference}"""
	refs = {}
	for variable_name, (value, dark_value) in palette.items():
		name = frappe.db.exists("Builder Variable", {"variable_name": variable_name, "group": group})
		if name:
			doc = frappe.get_doc("Builder Variable", name)
		else:
			doc = frappe.new_doc("Builder Variable")
			doc.variable_name = variable_name
		doc.type = "Color"
		doc.value = value
		doc.dark_value = dark_value
		doc.group = group
		doc.save(ignore_permissions=True) if name else doc.insert(ignore_permissions=True)
		refs[variable_name] = f"var(--{doc.name}, {value})"
	return refs


def upsert_client_script(name: str, script_type: str, script: str) -> str:
	existing = frappe.db.exists("Builder Client Script", {"name": name})
	doc = frappe.get_doc("Builder Client Script", existing) if existing else frappe.new_doc("Builder Client Script")
	doc.update({"script_type": script_type, "script": script})
	if not existing:
		doc.name = name
	doc.save(ignore_permissions=True) if existing else doc.insert(ignore_permissions=True, set_name=name)
	return doc.name
