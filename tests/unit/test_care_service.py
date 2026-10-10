import pytest

from breedernear_core import care_service as svc
from breedernear_core.listing_service import ListingError
from breedernear_core.safety.welfare_rules import cage_is_big_enough
from breedernear_core.schemas import CarePlan, Phase

GUEST = "guest-priya"


@pytest.fixture(autouse=True)
def clear_cache():
    svc._care_cache.clear()


def kit_cage(kit):
    return next((i for i in kit["items"] if i["category"] == "cage"), None)


# Starter kit

@pytest.mark.parametrize("species,count", [("budgie", 2), ("lovebird", 4), ("cockatiel", 2),
                                           ("cockatiel", 6), ("zebra finch", 2), ("canary", 4)])
def test_kit_cage_always_meets_welfare_minimum(fakes, species, count):
    from breedernear_core.data import load_seed
    from breedernear_core.safety.species_rules import species_key_for
    kit = svc.build_starter_kit(species, count)
    cage = next(p for p in load_seed("products.json")["products"] if p["id"] == kit_cage(kit)["product_id"])
    assert cage_is_big_enough(tuple(cage["dimensions_cm"]), species_key_for(species), count)


def test_too_small_display_cage_is_never_chosen(fakes):
    kit = svc.build_starter_kit("budgie", 2)
    assert kit_cage(kit)["product_id"] != "PRD-CAGE-001"
    assert "Compact Bird Cage 45×30×40 cm" in kit["cages_excluded_as_too_small"]


def test_no_fitting_cage_gives_welfare_note_instead_of_a_small_cage(fakes):
    kit = svc.build_starter_kit("cockatiel", 8)
    assert kit_cage(kit) is None and "aviary" in kit["welfare_note"]


def test_kit_has_at_most_eight_items_and_a_correct_total(fakes):
    for species in ("budgie", "Labrador", "Shih Tzu", "Persian cat"):
        kit = svc.build_starter_kit(species, 1)
        assert 4 <= len(kit["items"]) <= 8
        assert kit["total_inr"] == sum(i["price_inr"] * i["quantity"] for i in kit["items"])


def test_kit_matches_species(fakes):
    kit = svc.build_starter_kit("Labrador", 1)
    ids = {i["product_id"] for i in kit["items"]}
    assert "PRD-DBED-001" in ids and "PRD-DBED-003" not in ids      # large bed, not the small one


def test_kit_never_includes_breeding_or_medical_products(fakes):
    for species in ("budgie", "lovebird", "Labrador", "Persian cat"):
        cats = {i["category"] for i in svc.build_starter_kit(species, 2)["items"]}
        assert "breeding" not in cats


def test_protected_and_unknown_species_are_refused(fakes):
    with pytest.raises(ListingError, match="protected"):
        svc.build_starter_kit("pachai kili", 1)
    with pytest.raises(ListingError, match="Available"):
        svc.build_starter_kit("giraffe", 1)


def test_catalogue_brands_are_the_checked_fictional_ones():
    from breedernear_core.data import load_seed
    brands = {p["brand"] for p in load_seed("products.json")["products"]}
    assert brands == {"Featherhaven", "Tailnook", "PawNest", "Whiskerwell"}


# Care plan

def test_care_plan_appends_disclaimer_in_code(fakes):
    r = svc.care_plan("budgie", 4)
    assert r["care_plan"]["disclaimer"] == svc.DISCLAIMER
    assert len(r["care_plan"]["see_vet_if"]) >= 3
    assert "Budgerigar" in fakes[2].care_calls[0] and "4 months" in fakes[2].care_calls[0]


def test_care_plan_removes_medicine_dosing_lines(fakes):
    vision = fakes[2]
    vision.plan.diet.append("Give 2 ml multivitamin dose daily")
    vision.plan.phases[0].steps.append("Start an antibiotic course")
    plan = svc.care_plan("budgie", 4)["care_plan"]
    lines = plan["diet"] + plan["daily_routine"] + plan["see_vet_if"] + [
        step for phase in plan["phases"] for step in phase["steps"]]
    assert not any(svc._MEDICAL.search(line) for line in lines)
    assert "Seed mix with fresh greens" in plan["diet"]


def test_care_plan_without_enough_vet_signs_is_an_error(fakes):
    vision = fakes[2]
    vision.plan = CarePlan.model_construct(
        species="Budgerigar", diet=[], daily_routine=[], disclaimer="",
        phases=[Phase(title="Days 0-2", steps=["Rest"])],
        see_vet_if=["Fluffed up", "Give 5 mg tablets", "Antibiotic if sneezing"])
    with pytest.raises(ListingError):
        svc.care_plan("budgie", None)


def test_care_plan_schema_requires_vet_signs():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        CarePlan(species="x", phases=[], diet=[], daily_routine=[], see_vet_if=[])


def test_care_plan_is_cached_per_species_and_age(fakes):
    svc.care_plan("budgie", 4)
    svc.care_plan("budgie", 4)
    assert len(fakes[2].care_calls) == 1


# Cart

def test_add_and_view_cart(fakes):
    r = svc.add_to_cart(GUEST, ["PRD-CAGE-002", "PRD-FOOD-001"])
    assert r["total_inr"] == 1499 + 249
    assert "no payments" in r["note"]
    r = svc.add_to_cart(GUEST, ["PRD-FOOD-001"])
    assert {i["product_id"]: i["quantity"] for i in r["items"]}["PRD-FOOD-001"] == 2


def test_cart_limits(fakes):
    with pytest.raises(ListingError):
        svc.add_to_cart(GUEST, ["PRD-NOPE"])
    with pytest.raises(ListingError):
        svc.add_to_cart(GUEST, ["PRD-CAGE-006"], quantity=4)        # only 3 in stock
    with pytest.raises(ListingError):
        svc.add_to_cart(GUEST, [])


def test_carts_are_per_guest_and_removable(fakes):
    svc.add_to_cart(GUEST, ["PRD-FOOD-001"])
    assert svc.view_cart("someone-else")["items"] == []
    assert svc.remove_from_cart(GUEST, "PRD-FOOD-001")["items"] == []
