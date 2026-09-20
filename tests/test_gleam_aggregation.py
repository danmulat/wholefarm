import numpy as np

from wholefarm.gleam_aggregation import (
    calc_allocated_emissions,
    calc_co2eq,
    calc_cohort_totals,
)

FEED = [{"emissions_source": "co2_ration_fertilizer"}]


def test_cohort_total_rules_match_pinned_gleam() -> None:
    assert calc_cohort_totals(
        value=100.0,
        cohort_stock_size=50.0,
        ration_intake=10.0,
        feed_emissions_list=FEED,
        simulation_duration=365.0,
        variable_name="milk_production_mass_cohort",
        variable_type="Production",
    ) == 100.0

    feed_total = calc_cohort_totals(
        value=2.0,
        cohort_stock_size=50.0,
        ration_intake=10.0,
        feed_emissions_list=FEED,
        simulation_duration=365.0,
        variable_name="co2_ration_fertilizer",
        variable_type="Emissions",
    )
    assert feed_total == 2.0 * 10.0 * 50.0 * 365.0 / 1000.0


def test_allocated_emissions_matches_reference_vector_case() -> None:
    result = calc_allocated_emissions(
        [1000.0, 500.0, 200.0],
        [0.6, 0.4, 0.8],
    )
    assert np.allclose(result, [600.0, 200.0, 160.0])


def test_gleam_ar6_conversion_uses_pinned_values() -> None:
    ch4 = calc_co2eq("CH4", 100.0, "AR6")
    n2o = calc_co2eq("N2O", 10.0, "AR6")
    assert ch4["value_co2eq"] == 2700.0
    assert ch4["gwp"] == 27.0
    assert n2o["value_co2eq"] == 2730.0
    assert n2o["gwp"] == 273.0


def test_gleam_co2eq_vectorized_reference_case() -> None:
    result = calc_co2eq(
        ["CH4", "N2O", "CO2"],
        [100.0, 10.0, 1000.0],
        "AR6",
    )
    assert np.allclose(result["gwp"], [27.0, 273.0, 1.0])
    assert np.allclose(result["value_co2eq"], [2700.0, 2730.0, 1000.0])