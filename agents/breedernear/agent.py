from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini

from breedernear_core.config import agents_model, retry_options
from breedernear_core.tools.care import add_to_cart, build_starter_kit, care_plan, view_cart
from breedernear_core.tools.companion import (
    add_pet_weight,
    check_pet_symptoms,
    log_today,
    my_pets,
    pet_overview,
)
from breedernear_core.tools.listing import (
    check_external_listing,
    extract_listing,
    my_listings,
    publish_listing,
    update_draft,
)
from breedernear_core.tools.match import (
    book_visit,
    create_enquiry,
    draft_enquiry_reply,
    draft_first_message,
    explain_screening,
    get_listing,
    mark_pet_bought,
    my_enquiries,
    my_visits,
    recommend_species,
    save_buyer_profile,
    search_listings,
)
from breedernear_core.tools.verification import (
    check_facility_photos,
    check_registration_certificate,
    verification_status,
)

from .callbacks import add_context, guard_reply, log_tool
from .prompts import (
    CARE_INSTRUCTION,
    COMPANION_INSTRUCTION,
    CONCIERGE_INSTRUCTION,
    LISTING_INSTRUCTION,
    MATCH_INSTRUCTION,
    TRUST_INSTRUCTION,
    VERIFICATION_INSTRUCTION,
)

# One model object for every agent, retrying capacity errors (429/5xx) with backoff.
MODEL = Gemini(model=agents_model(), retry_options=retry_options())
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
    tools=[recommend_species, search_listings, get_listing, create_enquiry, save_buyer_profile,
           draft_first_message, book_visit, my_visits, mark_pet_bought],
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

verification_agent = LlmAgent(
    name="verification_agent",
    model=MODEL,
    description="Helps sellers earn the Verified breeder badge: progress, facility photos and the "
                "dog-breeder registration certificate (no ID documents).",
    instruction=VERIFICATION_INSTRUCTION,
    tools=[verification_status, check_facility_photos, check_registration_certificate],
    **GUARDS,
)

companion_agent = LlmAgent(
    name="companion_agent",
    model=MODEL,
    description="Care companion for a pet the customer has bought: daily log, weight, health calendar and "
                "how urgently to see a vet. Never medicines or doses.",
    instruction=COMPANION_INSTRUCTION,
    tools=[my_pets, pet_overview, log_today, add_pet_weight, check_pet_symptoms],
    **GUARDS,
)

root_agent = LlmAgent(
    name="breedernear_concierge",
    model=MODEL,
    description="Greets users, detects whether they are buying or breeding, and routes them.",
    instruction=CONCIERGE_INSTRUCTION,
    sub_agents=[listing_agent, trust_agent, match_agent, care_agent, verification_agent, companion_agent],
    **GUARDS,
)
