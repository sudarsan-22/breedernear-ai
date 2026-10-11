"""ADK tools for the verification agent (sellers): the same service as Farm → Verification."""

from google.adk.tools import ToolContext

from breedernear_core import verification_service as svc
from breedernear_core.tools.listing import _safe, role_error


def verification_status(tool_context: ToolContext) -> dict:
    """Show the seller's verification: phone, facility photos and (dog breeders) registration certificate,
    each passed / not passed / pending with its reason, and the overall status."""
    if denied := role_error(tool_context, "seller"):
        return denied
    return _safe(svc.status_of, tool_context.user_id)


def check_facility_photos(upload_ids: list[str], tool_context: ToolContext) -> dict:
    """Review 1 to 5 photos of where the seller's animals live (space, cleanliness, crowding, condition).

    Args:
        upload_ids: IDs from the "[attachments upload_ids=...]" note.
    """
    if denied := role_error(tool_context, "seller"):
        return denied
    return _safe(svc.review_facility, tool_context.user_id, upload_ids)


def check_registration_certificate(upload_id: str, tool_context: ToolContext) -> dict:
    """Read a dog breeder's State Animal Welfare Board registration certificate and check it.

    Args:
        upload_id: The certificate photo's ID from the "[attachments upload_ids=...]" note.
    """
    if denied := role_error(tool_context, "seller"):
        return denied
    return _safe(svc.review_certificate, tool_context.user_id, upload_id)
