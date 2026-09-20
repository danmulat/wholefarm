from wholefarm.accounting import (
    CarbonStockChange,
    FarmGHGInventory,
    FarmScenarioResult,
    LivestockGHG,
    ScenarioComparison,
)


def test_intervention_benefit() -> None:
    baseline = FarmScenarioResult(
        "baseline",
        FarmGHGInventory(
            livestock=LivestockGHG(10, 2, 1, 3),
            soil_n2o_co2e_t=4,
        ),
        CarbonStockChange(soil_co2e_t=1),
    )
    intervention = FarmScenarioResult(
        "intervention",
        FarmGHGInventory(
            livestock=LivestockGHG(8, 1, 0.8, 2.5),
            soil_n2o_co2e_t=3,
        ),
        CarbonStockChange(soil_co2e_t=2),
    )
    assert ScenarioComparison(baseline, intervention).total_climate_benefit_co2e_t > 0
