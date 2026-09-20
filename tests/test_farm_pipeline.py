from wholefarm.accounting import LivestockGHG
from wholefarm.farm_pipeline import (
    FarmScenarioInputs,
    build_farm_scenario,
    compare_farm_scenarios,
    soc_stock_change_co2e_t,
)
from wholefarm.livestock_farm import LivestockFarmResult


def _livestock(total_scale: float) -> LivestockFarmResult:
    return LivestockFarmResult(
        ghg=LivestockGHG(
            enteric_ch4_co2e_t=10.0 * total_scale,
            manure_ch4_co2e_t=2.0 * total_scale,
            manure_n2o_co2e_t=1.0 * total_scale,
            feed_production_co2e_t=3.0 * total_scale,
        ),
        enteric_ch4_kg=0.0,
        manure_ch4_kg=0.0,
        manure_n2o_kg=0.0,
        feed_co2_kg=0.0,
        feed_n2o_kg=0.0,
        feed_ch4_kg=0.0,
        nitrogen_intake_kg=0.0,
        nitrogen_excretion_kg=0.0,
        volatile_solids_kg=0.0,
        milk_fpcm_kg=1000.0,
        meat_live_weight_kg=100.0,
        meat_carcass_weight_kg=50.0,
        fibre_kg=0.0,
        feed_emission_profile_complete=True,
        cohort_results=(),
    )


def test_soc_change_conversion() -> None:
    value = soc_stock_change_co2e_t(50.0, 51.0, 10.0)
    assert value == 10.0 * 44.0 / 12.0


def test_build_scenario_preserves_production_and_soc_change() -> None:
    result = build_farm_scenario(
        FarmScenarioInputs(
            scenario_name="baseline",
            livestock=_livestock(1.0),
            area_ha=10.0,
            initial_soc_t_c_ha=50.0,
            final_soc_t_c_ha=50.5,
            soil_n2o_co2e_t=4.0,
        )
    )
    assert result.production["milk_fpcm_kg"] == 1000.0
    assert result.removals.soil_co2e_t > 0
    assert result.emissions.gross_co2e_t == 20.0


def test_scenario_comparison_combines_emission_and_removal_changes() -> None:
    baseline = FarmScenarioInputs(
        scenario_name="baseline",
        livestock=_livestock(1.0),
        area_ha=10.0,
        initial_soc_t_c_ha=50.0,
        final_soc_t_c_ha=50.0,
        soil_n2o_co2e_t=4.0,
    )
    intervention = FarmScenarioInputs(
        scenario_name="intervention",
        livestock=_livestock(0.8),
        area_ha=10.0,
        initial_soc_t_c_ha=50.0,
        final_soc_t_c_ha=51.0,
        soil_n2o_co2e_t=3.0,
    )
    comparison = compare_farm_scenarios(baseline, intervention)
    assert comparison.gross_emission_reduction_co2e_t > 0
    assert comparison.additional_removals_co2e_t > 0
    assert comparison.total_climate_benefit_co2e_t > 0
