from google.adk.agents import LlmAgent

from breedernear_core.config import get_settings
from breedernear_core.tools.care import add_to_cart, build_starter_kit, care_plan, view_cart
from breedernear_core.tools.listing import (
    check_external_listing,
    extract_listing,
    my_listings,
    publish_listing,
    update_draft,
)
from breedernear_core.tools.match import (
    create_enquiry,
    draft_enquiry_reply,
    explain_screening,
    get_listing,
    my_enquiries,
    recommend_species,
    search_listings,
)

from .callbacks import add_context, guard_reply, log_tool
from .prompts import (
    CARE_INSTRUCTION,
    CONCIERGE_INSTRUCTION,
    LISTING_INSTRUCTION,
    MATCH_INSTRUCTION,
    TRUST_INSTRUCTION,
)

MODEL = get_settings().breedernear_model
# Every agent: context note before the model, reply guard after it, a log line before each tool.
GUARDS = {"before_model_callback": add_context, "after_model_callback": guard_reply,
          "before_tool_callback": log_tool}

listing_agent = LlmAgent(
    name="listing_agent",
    model=MODEL,
    description="Breeder listing assistant: turns a breeder's photos and casual message (English/Tamil) "
                "into a structured, fairly priced listing and publishes it after trust screening.",
    instruction=LISTING_INSTRUCTION,
    tools=[extract_listing, update_draft, publish_listing, my_listings, my_enquiries, draft_enquiry_reply],
    **GUARDS,
)

trust_agent = LlmAgent(
    name="trust_agent",
    model=MODEL,
    description="Checks pet-sale posts seen on WhatsApp, Instagram or Facebook for legality, scam and "
                "welfare warning signs, and explains the trust result.",
    instruction=TRUST_INSTRUCTION,
    tools=[check_external_listing, explain_screening],
    **GUARDS,
)

match_agent = LlmAgent(
    name="match_agent",
    model=MODEL,
    description="Helps buyers choose a suitable pet for their home and finds trusted breeder listings "
                "nearby at fair prices; sends enquiries to breeders.",
    instruction=MATCH_INSTRUCTION,
    tools=[recommend_species, search_listings, get_listing, create_enquiry],
    **GUARDS,
)

care_agent = LlmAgent(
    name="care_agent",
    model=MODEL,
    description="Builds a personalised starter kit and a first-14-days care plan for a newly chosen pet, "
                "and manages the demo cart.",
    instruction=CARE_INSTRUCTION,
    tools=[build_starter_kit, care_plan, add_to_cart, view_cart],
    **GUARDS,
)

root_agent = LlmAgent(
    name="breedernear_concierge",
    model=MODEL,
    description="Greets users, detects whether they are buying or breeding, and routes them.",
    instruction=CONCIERGE_INSTRUCTION,
    sub_agents=[listing_agent, trust_agent, match_agent, care_agent],
    **GUARDS,
)
