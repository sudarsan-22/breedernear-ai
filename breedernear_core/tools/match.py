"""ADK tools for the buyer match agent and the breeder inbox."""

from google.adk.tools import ToolContext

from breedernear_core import match_service as svc
from breedernear_core.tools.listing import _safe

DISTRICT_KEY = "buyer_district"
CHOSEN_KEY = "chosen_listing_id"


def recommend_species(animal_group: str, home_type: str, has_young_children: bool, first_time_owner: bool,
                      time_per_day_minutes: int, noise_ok: bool, budget_inr: int,
                      tool_context: ToolContext) -> dict:
    """Shortlist pet species that suit the buyer's home, family, time and budget (rule-based).

    Args:
        animal_group: "bird", "dog", "cat" or "any".
        home_type: "flat" or "house".
        has_young_children: True if children under about 12 live in the home.
        first_time_owner: True if the buyer has not kept this kind of pet before.
        time_per_day_minutes: Time the family can spend on care each day, in minutes.
        noise_ok: False if noise would be a problem (e.g. close neighbours).
        budget_inr: Budget for the animal itself in rupees. Use 0 if not known.
    """
    return _safe(svc.recommend_species, animal_group, home_type, has_young_children, first_time_owner,
                 time_per_day_minutes, noise_ok, budget_inr or None)


def search_listings(species: str, district: str, max_price_inr: int, tool_context: ToolContext) -> dict:
    """Find published listings near the buyer, trusted first, then by distance and price (max 4).

    Args:
        species: Species or group the buyer wants, e.g. "budgie", "lovebird", "Labrador", "bird".
        district: The buyer's district or city, e.g. "Tiruppur".
        max_price_inr: Highest price per unit the buyer will pay. Use 0 for no limit.
    """
    result = _safe(svc.search_listings, tool_context.user_id, species, district, max_price_inr or None)
    if result.get("status") == "ok":
        tool_context.state[DISTRICT_KEY] = result["district"]
    return result


def get_listing(listing_id: str, tool_context: ToolContext) -> dict:
    """Show one listing's details: screening checks, health notes, breeder and questions to ask.

    Args:
        listing_id: The listing ID from search results, e.g. "LST-0012".
    """
    result = _safe(svc.get_listing, tool_context.user_id, listing_id)
    if result.get("status") == "ok":
        tool_context.state[CHOSEN_KEY] = listing_id
    return result


def create_enquiry(listing_id: str, message: str, tool_context: ToolContext) -> dict:
    """Send the buyer's enquiry to the breeder of a listing (demo: saved to the breeder inbox).

    Args:
        listing_id: The listing the buyer is interested in.
        message: The buyer's message to the breeder, without phone numbers or addresses.
    """
    result = _safe(svc.create_enquiry, tool_context.user_id, listing_id, message)
    if result.get("status") == "ok":
        tool_context.state[CHOSEN_KEY] = listing_id
    return result


def my_enquiries(tool_context: ToolContext) -> dict:
    """List enquiries buyers have sent about this breeder's own listings."""
    return _safe(svc.my_enquiries, tool_context.user_id)
