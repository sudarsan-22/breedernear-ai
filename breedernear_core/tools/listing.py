"""ADK tools for the breeder listing assistant and the trust agent."""

from google.adk.tools import ToolContext

from breedernear_core import accounts
from breedernear_core import listing_service as svc

DRAFT_KEY = "draft_listing_id"


def _safe(fn, *args) -> dict:
    try:
        return fn(*args)
    except svc.ListingError as e:
        return {"status": "error", "message": str(e)}
    except accounts.AccountError as e:
        return {"status": "error", "message": str(e)}


def role_error(tool_context: ToolContext, role: str) -> dict | None:
    """Check the caller's real role from the database (never trust the conversation)."""
    try:
        accounts.require_role(accounts.get_user(tool_context.user_id), role)
    except accounts.AccountError as e:
        return {"status": "error", "role_required": role, "message": str(e)}
    return None


def extract_listing(text: str, upload_ids: list[str], tool_context: ToolContext) -> dict:
    """Turn a breeder's message and photos into a structured listing draft with a fair-price range.

    Args:
        text: The breeder's message exactly as written (any language).
        upload_ids: IDs of the uploaded photos from the [attachments upload_ids=...] note. May be empty.
    """
    if denied := role_error(tool_context, "seller"):
        return denied
    result = _safe(svc.extract_listing, tool_context.user_id, text, upload_ids)
    if result.get("status") == "ok":
        tool_context.state[DRAFT_KEY] = result["draft_id"]
    return result


def update_draft(field: str, value: str, tool_context: ToolContext) -> dict:
    """Change one field of the current listing draft, e.g. price_inr, age_months or health_notes.

    Args:
        field: The draft field to change.
        value: The new value, as text.
    """
    if denied := role_error(tool_context, "seller"):
        return denied
    draft_id = tool_context.state.get(DRAFT_KEY)
    if not draft_id:
        return {"status": "error", "message": "There is no draft yet. Describe the animals first."}
    return _safe(svc.update_draft, tool_context.user_id, draft_id, field, value)


def publish_listing(tool_context: ToolContext) -> dict:
    """Run the trust and compliance screening on the current draft and publish it if allowed."""
    if denied := role_error(tool_context, "seller"):
        return denied
    draft_id = tool_context.state.get(DRAFT_KEY)
    if not draft_id:
        return {"status": "error", "message": "There is no draft to publish yet."}
    seller = accounts.get_user(tool_context.user_id) or {}
    farm_name = (seller.get("farm") or {}).get("farm_name") or seller.get("name")
    result = _safe(svc.publish_listing, tool_context.user_id, draft_id, tool_context.state.get("device_id"),
                   farm_name)
    if result.get("status") == "ok":
        tool_context.state[DRAFT_KEY] = None
    return result


def my_listings(tool_context: ToolContext) -> dict:
    """List this breeder's listings with their trust level."""
    if denied := role_error(tool_context, "seller"):
        return denied
    return _safe(svc.my_listings, tool_context.user_id)


def check_external_listing(text: str, upload_ids: list[str], tool_context: ToolContext) -> dict:
    """Check a pet-sale post seen elsewhere (WhatsApp, Instagram, Facebook) for warning signs.

    Args:
        text: The post text the buyer pasted. May be empty if only a screenshot was uploaded.
        upload_ids: IDs of uploaded screenshots or photos. May be empty.
    """
    return _safe(svc.check_external_listing, tool_context.user_id, text, upload_ids)
