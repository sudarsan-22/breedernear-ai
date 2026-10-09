import pytest

from breedernear_core.safety.price_rules import assess_price, price_range
from breedernear_core.safety.scam_rules import find_scam_signals
from breedernear_core.safety.welfare_rules import cage_is_big_enough, min_cage_cm


@pytest.mark.parametrize("text", [
    "Full advance only, then we send",
    "100% advance payment, courier only",
    "Pay first via GPay",
    "No visit please, parcel only",
    "advance mattum, courier mattum",
    "Visit illa, today only offer",
    "Delivery all over India available",
])
def test_scam_signals_detected(text):
    assert find_scam_signals(text), text


@pytest.mark.parametrize("text", [
    "4 lutino lovebird pairs, 5 months, ₹1800 per pair, Saibaba Colony",
    "Visit our aviary any evening. Pay after you see the birds.",
    "",
])
def test_normal_text_has_no_scam_signals(text):
    assert find_scam_signals(text) == []


def test_price_range_lookup_uses_variety_then_default():
    assert price_range("lovebird_peach_faced", "Lutino") == (1500, 3000)
    assert price_range("lovebird_peach_faced", "unknown colour") == (1200, 2500)
    assert price_range("unknown_species") is None
    assert price_range(None) is None


@pytest.mark.parametrize("price,result,penalty", [
    (500, "warn", 30),     # < 50% of 1200
    (1000, "warn", 10),    # below minimum
    (1800, "pass", 0),     # within range
    (4000, "info", 5),     # > 150% of 2500
])
def test_price_assessment(price, result, penalty):
    check = assess_price(price, (1200, 2500))
    assert (check.result, check.penalty) == (result, penalty)


def test_price_missing_or_no_range_is_info_only():
    assert assess_price(None, (1, 2)).result == "info"
    assert assess_price(1000, None).result == "info"


def test_min_cage_grows_with_number_of_pairs():
    one_pair = min_cage_cm("budgerigar", 2)
    two_pairs = min_cage_cm("budgerigar", 4)
    assert two_pairs[0] > one_pair[0]
    assert min_cage_cm("labrador", 1) is None


def test_small_cage_is_rejected_and_large_cage_accepted():
    assert not cage_is_big_enough((40, 30, 30), "lovebird_peach_faced", 2)
    assert cage_is_big_enough((80, 50, 60), "lovebird_peach_faced", 2)
