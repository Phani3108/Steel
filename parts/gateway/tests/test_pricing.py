"""Modeled-cost pricing: a true function of token usage, never zero for real work."""

from steel_gateway.pricing import RATES_PER_MTOK, estimate_tokens, modeled_cost


def test_cost_scales_with_tokens_and_is_positive():
    small = modeled_cost("reasoning", 100, 50)
    big = modeled_cost("reasoning", 1000, 500)
    assert 0 < small < big  # more tokens cost more


def test_output_priced_higher_than_input():
    in_rate, out_rate = RATES_PER_MTOK["reasoning"]
    assert out_rate > in_rate
    assert modeled_cost("reasoning", 0, 1000) > modeled_cost("reasoning", 1000, 0)


def test_group_rates_differ():
    # fast is cheaper than the reasoning tiers for identical usage
    assert modeled_cost("fast", 1000, 1000) < modeled_cost("reasoning", 1000, 1000)
    assert modeled_cost("reasoning", 1000, 1000) < modeled_cost("reasoning-max", 1000, 1000)


def test_unknown_group_falls_back_to_a_default_rate():
    assert modeled_cost("mystery", 1000, 1000) > 0


def test_estimate_tokens_is_proportional_and_at_least_one():
    assert estimate_tokens("") == 1
    assert estimate_tokens("a" * 400) == 100  # ~4 chars/token
