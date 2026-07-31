import frappe

from shop import personas
from shop.api import only_managers


@frappe.whitelist()
def get_personas() -> list[dict]:
	only_managers()
	return personas.all_personas()


@frappe.whitelist(methods=["POST"])
def prepare(persona: str) -> dict:
	only_managers()
	return personas.prepare(persona)
