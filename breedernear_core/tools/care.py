"""ADK tools for the care agent: starter kit, care plan and the demo cart."""

from google.adk.tools import ToolContext

from breedernear_core import care_service as svc
from breedernear_core.tools.listing import _safe


def build_starter_kit(species: str, count: int, tool_context: ToolContext) -> dict:
    """Build a starter kit (max 8 products) with a total. Cage size follows the welfare minimums.

    Args:
        species: The pet species, e.g. "budgie", "lovebird", "Labrador".
        count: Number of animals (one pair = 2).
    """
    return _safe(svc.build_starter_kit, species, count)


def care_plan(species: str, age_months: int, tool_context: ToolContext) -> dict:
    """Write a first-14-days care plan with vet warning signs for a newly chosen pet.

    Args:
        species: The pet species.
        age_months: Age of the pet in months. Use -1 if not known.
    """
    return _safe(svc.care_plan, species, age_months)


def add_to_cart(product_ids: list[str], tool_context: ToolContext) -> dict:
    """Add products to the buyer's demo cart (quantity 1 each). No payment is taken.

    Args:
        product_ids: Product IDs from the starter kit, e.g. ["PRD-CAGE-002"].
    """
    return _safe(svc.add_to_cart, tool_context.user_id, product_ids)


def view_cart(tool_context: ToolContext) -> dict:
    """Show the buyer's demo cart with the total."""
    return _safe(svc.view_cart, tool_context.user_id)
