from wholefarm.gleam_feed import (
    aggregate_ration_components,
    calc_ch4_ration_rice,
    calc_co2_ration_fertilizer,
    calc_n2o_ration_manure,
)


def test_weighted_feed_emission_reference_cases() -> None:
    assert calc_co2_ration_fertilizer(0.6, 10) == 6
    assert calc_n2o_ration_manure(0.6, 10) == 6
    assert calc_ch4_ration_rice(0.6, 10) == 6


def test_missing_feed_factor_is_preserved() -> None:
    assert calc_co2_ration_fertilizer(0.6, None) is None


def test_ration_component_aggregation() -> None:
    assert aggregate_ration_components([2.0, None, 3.0]) == 5.0
