import json

import frappe

from shop.agent.setup import AGENT_TITLE
from shop.api import only_managers


@frappe.whitelist(methods=["POST"])
def send(message: str, session: str | None = None) -> dict:
	"""Ask the store assistant to do something. Returns the run, which may pause for confirmation."""
	only_managers()
	from flow.api.api import start_run

	run = start_run(input=message, agent=AGENT_TITLE, session=session)
	return decorate(run)


@frappe.whitelist(methods=["POST"])
def answer(run: str, answers: dict) -> dict:
	"""Reply to a paused run, for example confirming a change the assistant proposed."""
	only_managers()
	from flow.api.api import resume_run

	return decorate(resume_run(run_name=run, answers=answers))


@frappe.whitelist(methods=["POST"])
def stop(run: str) -> dict:
	only_managers()
	from flow.api.api import stop_run

	return stop_run(run_name=run)


def decorate(run: dict) -> dict:
	run["messages"] = transcript(run.get("session"))
	return run


@frappe.whitelist()
def get_session(session: str) -> dict:
	only_managers()
	return {"session": session, "messages": transcript(session)}


def transcript(session: str | None) -> list[dict]:
	if not session:
		return []
	rows = frappe.get_all(
		"Flow Session Message",
		filters={"parent": session},
		fields=["role", "content", "tool_calls", "run"],
		order_by="idx",
	)
	messages = []
	for row in rows:
		# the system turn carries the agent's instructions and is not part of the conversation
		if row.role in ("tool", "system"):
			continue
		calls = tool_names(row.tool_calls)
		if not (row.content or calls):
			continue
		messages.append({"role": row.role, "content": row.content, "tools": calls})
	return messages


def tool_names(raw: str | None) -> list[str]:
	if not raw:
		return []
	try:
		calls = json.loads(raw)
	except ValueError:
		return []
	return [call.get("function", {}).get("name") for call in calls if call.get("function")]


@frappe.whitelist()
def list_sessions(limit: int = 20) -> list[dict]:
	only_managers()
	return frappe.get_all(
		"Flow Session",
		filters={"owner": frappe.session.user},
		fields=["name", "title", "modified"],
		order_by="modified desc",
		limit=limit,
	)
