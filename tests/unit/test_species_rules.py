import pytest

from breedernear_core.safety.species_rules import find_cites, find_protected, species_key_for


@pytest.mark.parametrize("text", [
    "Indian ringneck chicks for sale",
    "rose ringed parakeet 2 nos",
    "Psittacula krameri pair",
    "pachai kili kunjugal virpanaikku",
    "Munia birds available, 50 rs each",
    "Indian silverbill pair",
    "strawberry finch red munia",
    "Talking hill myna",
    "Alexandrine parakeet male",
    "Parakeet chicks hand fed",           # generic term, no exotic named
    "Star tortoise baby",
])
def test_protected_species_are_detected(text):
    assert find_protected(text), text


@pytest.mark.parametrize("text", [
    "Budgie pair, normal colour",
    "4 lutino lovebird pairs, 5 months",
    "Cockatiel pied pair",
    "Zebra finch 3 pairs",
    "Society finch pair",                 # domestic look-alike of a munia
    "Society munia pair",
    "budgie parakeet hand tamed",          # generic word + allowed exotic
    "Panchavarna kili (macaw)",            # Tamil name for macaw
    "Labrador puppies, 45 days",
    "",
])
def test_allowed_species_are_not_blocked(text):
    assert not find_protected(text), text


def test_matching_ignores_case_and_punctuation():
    assert find_protected("ROSE-RINGED   PARAKEET!!!")


def test_model_species_guess_is_also_checked():
    assert find_protected("lovebirds for sale", "Rose-ringed parakeet")


@pytest.mark.parametrize("text,expected", [
    ("African grey talking parrot", "african_grey"),
    ("Fischer's lovebird pair", "fischers_lovebird"),
    ("Sun conure baby", "conure"),
    ("Blue and gold macaw", "macaw"),
])
def test_cites_species_are_detected(text, expected):
    assert expected in [m.key for m in find_cites(text)]


@pytest.mark.parametrize("text", ["Budgie pair", "Peach faced lovebird", "Cockatiel", "Zebra finch"])
def test_common_pet_birds_are_not_cites(text):
    assert not find_cites(text)


@pytest.mark.parametrize("text,key", [
    ("lutino lovebird pair", "lovebird_peach_faced"),
    ("Fischer's lovebird", "lovebird_fischers"),
    ("budgies 2 pairs", "budgerigar"),
    ("Labrador puppy", "labrador"),
    ("mystery animal", None),
])
def test_species_key_mapping(text, key):
    assert species_key_for(text) == key
