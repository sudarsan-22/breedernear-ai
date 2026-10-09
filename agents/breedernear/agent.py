from google.adk.agents import LlmAgent

from breedernear_core.config import get_settings
from breedernear_core.tools.listing import (
    check_external_listing,
    extract_listing,
    my_listings,
    publish_listing,
    update_draft,
)

from .prompts import CONCIERGE_INSTRUCTION, LISTING_INSTRUCTION, TRUST_INSTRUCTION

MODEL = get_settings().breedernear_model

listing_agent = LlmAgent(
    name="listing_agent",
    model=MODEL,
    description="Breeder copilot: turns a breeder's photos and casual message (English/Tamil) into a "
                "structured, fairly priced listing and publishes it after trust screening.",
    instruction=LISTING_INSTRUCTION,
    tools=[extract_listing, update_draft, publish_listing, my_listings],
)

trust_agent = LlmAgent(
    name="trust_agent",
    model=MODEL,
    description="Checks pet-sale posts seen on WhatsApp, Instagram or Facebook for legality, scam and "
                "welfare warning signs, and explains the trust result.",
    instruction=TRUST_INSTRUCTION,
    tools=[check_external_listing],
)

root_agent = LlmAgent(
    name="breedernear_concierge",
    model=MODEL,
    description="Greets users, detects whether they are buying or breeding, and routes them.",
    instruction=CONCIERGE_INSTRUCTION,
    sub_agents=[listing_agent, trust_agent],
)
