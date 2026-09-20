from wholefarm.accounting import (
    CarbonStockChange,
    FarmGHGInventory,
    FarmScenarioResult,
    LivestockGHG,
    ScenarioComparison,
)
from wholefarm.cap2er import NitrogenIndicators
from wholefarm.carbon_agri import CarbonAgriGain
from wholefarm.reporting import (
    cap2er_level2_report,
    carbon_agri_report,
    summarize_comparison,
    summarize_scenario,
)


def _scenario(name: str, gross_scale: float, soil: float) -> FarmScenarioResult:
    return FarmScenarioResult(
        scenario_name=name,
        emissions=FarmGHGInventory(
            livestock=LivestockGHG(
                enteric_ch4_co2e_t=10.0 * gross_scale,
                manure_ch4_co2e_t=2.0 * gross_scale,
                manure_n2o_co2e_t=1.0 * gross_scale,
                feed_production_co2e_t=3.0 * gross_scale,
            ),
            soil_n2o_co2e_t=4.0 * gross_scale,
        ),
        removals=CarbonStockChange(soil_co2e_t=soil, tree_biomass_co2e_t=1.0),
        production={"milk_fpcm_kg": 1000.0, "meat_live_weight_kg": 100.0},
    )


def test_scenario_reporting_preserves_gross_net_and_intensity() -> None:
    report = summarize_scenario(_scenario("baseline", 1.0, 2.0))
    assert report.gross_ghg_t_co2e == 20.0
    assert report.total_removals_t_co2e == 3.0
    assert report.net_ghg_t_co2e == 17.0
    assert report.milk_intensity_kg_co2e_per_kg_fpcm == 20.0


def test_comparison_reporting_matches_accounting() -> None:
    comparison = ScenarioComparison(
        baseline=_scenario("baseline", 1.0, 2.0),
        intervention=_scenario("intervention", 0.8, 5.0),
    )
    report = summarize_comparison(comparison)
    assert report.gross_emission_reduction_t_co2e == 4.0
    assert report.additional_removals_t_co2e == 3.0
    assert report.total_climate_benefit_t_co2e == 7.0


def test_cap2er_report_keeps_uncomputed_indicators_visible() -> None:
    nitrogen = NitrogenIndicators(
        apparent_balance_kg_n_ha=20.0,
        efficiency_fraction=0.6,
        air_losses_kg_n_ha=4.0,
        soil_storage_kg_n_ha=3.0,
        leaching_potential_kg_n_ha=13.0,
    )
    report = cap2er_level2_report(_scenario("baseline", 1.0, 2.0), nitrogen)
    assert report["GHG emissions"].status == "computed"
    assert report["Nitrogen balance"].value == 20.0
    assert report["Treatment Frequency Index"].status == "not_computable"


def test_carbon_agri_report_is_separate_methodology_view() -> None:
    result = carbon_agri_report(
        CarbonAgriGain(
            footprint_gain_kg_co2e=1000.0,
            sequestration_gain_kg_co2e=500.0,
        ),
        project_years=5,
    )
    assert result["farm_carbon_gain_kg_co2e"] == 1500.0
    assert result["methodology"] == "CARBON AGRI"
