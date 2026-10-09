from google.adk.agents import LlmAgent

from breedernear_core.config import get_settings

from .prompts import CONCIERGE_INSTRUCTION

root_agent = LlmAgent(
    name="breedernear_concierge",
    model=get_settings().breedernear_model,
    description="Greets users, detects whether they are buying or breeding, and routes them.",
    instruction=CONCIERGE_INSTRUCTION,
)
