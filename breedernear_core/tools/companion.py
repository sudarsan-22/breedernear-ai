"""ADK tools for the care companion agent (customers who bought a pet): the same service as My pets."""

from google.adk.tools import ToolContext

from breedernear_core import companion_service as svc
from breedernear_core.tools.listing import _safe, role_error


def my_pets(tool_context: ToolContext) -> dict:
    """List the customer's pets with days at home and their log streak."""
    if denied := role_error(tool_context, "customer"):
        return denied
    return svc.list_pets(tool_context.user_id)


def pet_overview(pet_id: str, tool_context: ToolContext) -> dict:
    """One pet's recent logs, weights against typical ranges, this week's check-in and health calendar.

    Args:
        pet_id: The pet's ID from my_pets, e.g. "PET_DEMO_MANGO".
    """
    if denied := role_error(tool_context, "customer"):
        return denied
    result = _safe(svc.get_pet, tool_context.user_id, pet_id)
    if result.get("status") == "ok":
        result["logs"] = result["logs"][:5]
    return result


def log_today(pet_id: str, food: str, play: str, note: str, tool_context: ToolContext) -> dict:
    """Save today's care log; returns feedback on the food and tips for play.

    Args:
        pet_id: The pet's ID.
        food: What the pet ate today. Empty if not mentioned.
        play: How the pet played or exercised today. Empty if not mentioned.
        note: Anything else the owner mentioned. Empty if nothing.
    """
    if denied := role_error(tool_context, "customer"):
        return denied
    return _safe(svc.log_day, tool_context.user_id, pet_id, food, play, note)


def add_pet_weight(pet_id: str, value: float, tool_context: ToolContext) -> dict:
    """Record a weight (grams for birds, kilograms for dogs and cats) and compare it with the typical range.

    Args:
        pet_id: The pet's ID.
        value: The weight number in the pet's unit.
    """
    if denied := role_error(tool_context, "customer"):
        return denied
    return _safe(svc.add_weight, tool_context.user_id, pet_id, value)


def check_pet_symptoms(pet_id: str, description: str, tool_context: ToolContext) -> dict:
    """How urgently to see a vet about something the owner noticed (emergency, vet soon, or monitor).

    Args:
        pet_id: The pet's ID.
        description: What the owner notices, in their words.
    """
    if denied := role_error(tool_context, "customer"):
        return denied
    return _safe(svc.check_symptoms, tool_context.user_id, pet_id, description)
