"""Integration layer connecting livestock emissions and carbon stock changes."""

from __future__ import annotations

from dataclasses import dataclass

from .accounting import (
    CarbonStockChange,
    FarmGHGInventory,
    FarmScenarioResult,
    LivestockGHG,
    ScenarioComparison,
)
from .livestock_farm import LivestockFarmResult


@dataclass(frozen=True)
class FarmScenarioInputs:
    scenario_name: str
    livestock: LivestockFarmResult | None
    area_ha: float
    initial_soc_t_c_ha: float
    final_soc_t_c_ha: float
    tree_carbon_change_t_c: float = 0.0
    soil_n2o_co2e_t: float = 0.0
    crop_inputs_co2e_t: float = 0.0
    energy_co2e_t: float = 0.0
    purchased_inputs_co2e_t: float = 0.0
    other_co2e_t: float = 0.0

    def __post_init__(self) -> None:
        if self.area_ha <= 0:
            raise ValueError("area_ha must be positive")
        if self.initial_soc_t_c_ha < 0 or self.final_soc_t_c_ha < 0:
            raise ValueError("SOC stocks must be nonnegative")


def soc_stock_change_co2e_t(
    initial_soc_t_c_ha: float,
    final_soc_t_c_ha: float,
    area_ha: float,
    carbon_to_co2: float = 44.0 / 12.0,
) -> float:
    if initial_soc_t_c_ha < 0 or final_soc_t_c_ha < 0:
        raise ValueError("SOC stocks must be nonnegative")
    if area_ha <= 0:
        raise ValueError("area_ha must be positive")
    if carbon_to_co2 <= 0:
        raise ValueError("carbon_to_co2 must be positive")
    return (final_soc_t_c_ha - initial_soc_t_c_ha) * area_ha * carbon_to_co2


def build_farm_scenario(
    inputs: FarmScenarioInputs,
    carbon_to_co2: float = 44.0 / 12.0,
) -> FarmScenarioResult:
    soil_change = soc_stock_change_co2e_t(
        inputs.initial_soc_t_c_ha,
        inputs.final_soc_t_c_ha,
        inputs.area_ha,
        carbon_to_co2,
    )
    tree_change = inputs.tree_carbon_change_t_c * carbon_to_co2

    if inputs.livestock is None:
        production: dict[str, float] = {}
        livestock_ghg = LivestockGHG()
    else:
        production = {
            "milk_fpcm_kg": inputs.livestock.milk_fpcm_kg,
            "meat_live_weight_kg": inputs.livestock.meat_live_weight_kg,
            "meat_carcass_weight_kg": inputs.livestock.meat_carcass_weight_kg,
            "fibre_kg": inputs.livestock.fibre_kg,
        }
        livestock_ghg = inputs.livestock.ghg

    return FarmScenarioResult(
        scenario_name=inputs.scenario_name,
        emissions=FarmGHGInventory(
            livestock=livestock_ghg,
            soil_n2o_co2e_t=inputs.soil_n2o_co2e_t,
            crop_inputs_co2e_t=inputs.crop_inputs_co2e_t,
            energy_co2e_t=inputs.energy_co2e_t,
            purchased_inputs_co2e_t=inputs.purchased_inputs_co2e_t,
            other_co2e_t=inputs.other_co2e_t,
        ),
        removals=CarbonStockChange(
            soil_co2e_t=soil_change,
            tree_biomass_co2e_t=tree_change,
        ),
        production=production,
    )


def compare_farm_scenarios(
    baseline: FarmScenarioInputs,
    intervention: FarmScenarioInputs,
    carbon_to_co2: float = 44.0 / 12.0,
) -> ScenarioComparison:
    return ScenarioComparison(
        baseline=build_farm_scenario(baseline, carbon_to_co2),
        intervention=build_farm_scenario(intervention, carbon_to_co2),
    )