"""ADK callbacks shared by every BreederNear agent.

- before_model: adds a short context note (role, district, open draft, listing being discussed).
- after_model: replaces unsafe replies (medicine doses, protected species without a legal warning). In
  streaming mode it sees each partial chunk, so it tracks the reply so far, hides the rest of the stream
  once it turns unsafe, and replaces the final message (the web app shows the final text in place of the
  streamed one).
- before_tool: one structured log line per tool call for Cloud Logging, free text redacted.
"""

from google.genai import types

from breedernear_core.guardrails import redact_args, unsafe_reply
from breedernear_core.logs import emit
from breedernear_core.tools.listing import DRAFT_KEY
from breedernear_core.tools.match import CHOSEN_KEY, DISTRICT_KEY

SO_FAR = "temp:reply_so_far"          # temp: keys live for one invocation and are never stored
HIDDEN = "temp:reply_hidden"


def _text(llm_response) -> str:
    content = llm_response.content
    return "".join(p.text or "" for p in (content.parts or []) if not getattr(p, "thought", False)) \
        if content else ""


def add_context(callback_context, llm_request):
    state = callback_context.state
    notes = [f"Signed-in account: {state.get('role') or 'unknown'}"]
    if district := state.get(DISTRICT_KEY) or state.get("district"):
        notes.append(f"user's district: {district}")
    if state.get(DRAFT_KEY):
        notes.append("an unpublished listing draft is open")
    if listing := state.get(CHOSEN_KEY):
        notes.append(f"listing being discussed: {listing}")
    llm_request.append_instructions(["Context (from the app, not the user): " + "; ".join(notes) + "."])
    return None


def guard_reply(callback_context, llm_response):
    state = callback_context.state
    text = _text(llm_response)
    if llm_response.partial:
        if state.get(HIDDEN):
            return _replace(llm_response, "")
        so_far = (state.get(SO_FAR) or "") + text
        state[SO_FAR] = so_far
        if unsafe_reply(so_far):
            state[HIDDEN] = True
            return _replace(llm_response, "")
        return None
    hidden, so_far = state.get(HIDDEN), state.get(SO_FAR) or ""
    state[SO_FAR], state[HIDDEN] = "", False
    safe = unsafe_reply(text) or (unsafe_reply(so_far) if hidden else None)
    if safe is None:
        return None
    emit("WARNING", event="reply_replaced", agent=callback_context.agent_name,
         reason="medicine" if "medicine" in safe else "protected_species")
    return _replace(llm_response, safe)


def _replace(llm_response, text: str):
    """Swap the reply's text; keep any tool calls in the same response."""
    parts = (llm_response.content.parts or []) if llm_response.content else []
    others = [p for p in parts if p.text is None or getattr(p, "thought", False)]
    llm_response.content = types.Content(role="model", parts=[types.Part(text=text), *others])
    return llm_response


def log_tool(tool, args, tool_context):
    emit("INFO", event="tool_call", agent=tool_context.agent_name, tool=tool.name,
         user=tool_context.user_id, role=tool_context.state.get("role"), args=redact_args(args))
    return None
