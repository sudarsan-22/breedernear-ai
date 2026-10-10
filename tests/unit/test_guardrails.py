"""Reply guard, context note, tool log and explain_screening."""

import json
from types import SimpleNamespace

import pytest
from google.adk.models import LlmRequest, LlmResponse
from google.genai import types

from agents.breedernear import callbacks as cb
from breedernear_core import match_service as svc
from breedernear_core.guardrails import MEDICINE_REPLY, PROTECTED_REPLY, redact_args, unsafe_reply
from breedernear_core.listing_service import ListingError


# ---------------------------------------------------------------- unsafe_reply
@pytest.mark.parametrize("text", [
    "Give 0.5 mg of enrofloxacin twice a day.",
    "Try Baytril in the water.",
    "Put 2 drops in each nostril.",
    "The usual amount is 10 mg/kg.",
])
def test_medicine_names_and_doses_are_replaced(text):
    assert unsafe_reply(text) == MEDICINE_REPLY


@pytest.mark.parametrize("text", [
    "I can't suggest medicines or doses. Please see an avian vet today.",
    "A cage of 60 x 45 cm suits a budgie pair. Change the water every morning.",
    "Rose-ringed parakeets are protected in India, so they can't be sold. Budgies are a great legal choice.",
    "",
])
def test_safe_replies_pass(text):
    assert unsafe_reply(text) is None


def test_protected_species_without_a_legal_warning_is_replaced():
    assert unsafe_reply("Sure! Indian ringneck chicks make lovely talking pets.") == PROTECTED_REPLY


# ---------------------------------------------------------------- guard_reply (ADK after_model)
def ctx(**state):
    return SimpleNamespace(state=dict(state), agent_name="care_agent")


def response(text: str, partial: bool = False) -> LlmResponse:
    return LlmResponse(content=types.Content(role="model", parts=[types.Part(text=text)]), partial=partial)


def shown(r: LlmResponse | None, original: LlmResponse) -> str:
    return "".join(p.text or "" for p in (r or original).content.parts)


def test_non_streaming_unsafe_reply_is_replaced():
    c, r = ctx(), response("Give 5 mg of doxycycline.")
    assert shown(cb.guard_reply(c, r), r) == MEDICINE_REPLY


def test_safe_reply_is_untouched():
    r = response("See an avian vet today.")
    assert cb.guard_reply(ctx(), r) is None


def test_streaming_hides_chunks_once_unsafe_and_replaces_the_final_text():
    c = ctx()
    chunks = ["Sneezing can be serious. ", "Give 0.", "5 mg of enro", "floxacin daily."]
    seen = []
    for chunk in chunks:
        r = response(chunk, partial=True)
        seen.append(shown(cb.guard_reply(c, r), r))
    assert seen[0] == chunks[0]               # safe so far: streamed as is
    assert seen[2:] == ["", ""]               # unsafe from "5 mg": the rest is hidden
    final = response("".join(chunks))
    assert shown(cb.guard_reply(c, final), final) == MEDICINE_REPLY
    assert c.state[cb.SO_FAR] == "" and c.state[cb.HIDDEN] is False   # ready for the next reply


def test_tool_calls_survive_a_replaced_reply():
    call = types.Part(function_call=types.FunctionCall(name="care_plan", args={"species": "budgie"}))
    r = LlmResponse(content=types.Content(role="model", parts=[types.Part(text="Give 2 drops."), call]))
    out = cb.guard_reply(ctx(), r)
    assert out.content.parts[0].text == MEDICINE_REPLY
    assert out.content.parts[1].function_call.name == "care_plan"


# ---------------------------------------------------------------- add_context (ADK before_model)
def test_context_note_has_role_district_and_listing():
    req = LlmRequest()
    cb.add_context(ctx(role="customer", buyer_district="tiruppur", chosen_listing_id="LST-0012"), req)
    note = str(req.config.system_instruction)
    assert "customer" in note and "tiruppur" in note and "LST-0012" in note


# ---------------------------------------------------------------- log_tool (ADK before_tool)
def test_tool_log_is_one_json_line_with_free_text_redacted(capsys):
    tool = SimpleNamespace(name="create_enquiry")
    tc = SimpleNamespace(agent_name="match_agent", user_id="USR_1", state={"role": "customer"})
    msg = "Hello, is the pair still available? My number is in my profile, please call."
    assert cb.log_tool(tool, {"listing_id": "LST-0001", "message": msg}, tc) is None
    line = json.loads(capsys.readouterr().out.strip())
    assert line["severity"] == "INFO" and line["tool"] == "create_enquiry"
    assert line["args"] == {"listing_id": "LST-0001", "message": f"<text, {len(msg)} chars>"}


def test_redact_keeps_ids_and_short_values():
    assert redact_args({"species": "budgie", "upload_ids": ["a", "b"]}) == {"species": "budgie",
                                                                            "upload_ids": ["a", "b"]}


# ---------------------------------------------------------------- explain_screening
def test_explain_screening_for_a_visible_listing(seeded):
    r = svc.explain_screening("guest-priya", "LST-0001")
    assert r["screening"]["trust_level"] in {"TRUSTED", "CAUTION"}
    assert r["screening"]["checks"] and not r["is_yours"]


def test_explain_screening_hides_blocked_listings_from_others(seeded):
    with pytest.raises(ListingError):
        svc.explain_screening("guest-priya", "LST-0037")


def test_seller_can_explain_their_own_blocked_listing(seeded):
    store = seeded[0]
    listing = store.get_listing("LST-0037")
    store.save_listing("LST-0037", {**listing, "owner_user_id": "seller-1"})
    r = svc.explain_screening("seller-1", "LST-0037")
    assert r["is_yours"] and r["listing_status"] == "BLOCKED"
    assert r["screening"]["trust_level"] == "BLOCKED"
