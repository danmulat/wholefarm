"""Whole farm research model."""

from .accounting import CarbonStockChange, FarmGHGInventory, FarmScenarioResult, ScenarioComparison
from .config import ModelConfig
from .farm_pipeline import (
    FarmScenarioInputs,
    build_farm_scenario,
    compare_farm_scenarios,
    soc_stock_change_co2e_t,
)
from .livestock_farm import (
    DietEmissionFactors,
    LivestockCohortSpec,
    LivestockFarmResult,
    run_livestock_farm,
)
from .nutrient_flow import ManureNutrientFlow, ManureRecoveryConfig, route_manure_to_fields
from .soc_stock import (
    SoilLayer,
    aggregate_soc_layers_t_c_ha,
    equivalent_soil_mass_change_t_c_ha,
    equivalent_soil_mass_soc_t_c_ha,
    fine_soil_mass_t_ha,
    reference_soil_mass_t_ha,
    soc_stock_t_c_ha,
)

__all__ = [
    "CarbonStockChange",
    "DietEmissionFactors",
    "FarmGHGInventory",
    "FarmScenarioInputs",
    "FarmScenarioResult",
    "LivestockCohortSpec",
    "LivestockFarmResult",
    "ManureNutrientFlow",
    "ManureRecoveryConfig",
    "ModelConfig",
    "ScenarioComparison",
    "SoilLayer",
    "aggregate_soc_layers_t_c_ha",
    "equivalent_soil_mass_change_t_c_ha",
    "equivalent_soil_mass_soc_t_c_ha",
    "fine_soil_mass_t_ha",
    "reference_soil_mass_t_ha",
    "build_farm_scenario",
    "compare_farm_scenarios",
    "route_manure_to_fields",
    "run_livestock_farm",
    "soc_stock_change_co2e_t",
    "soc_stock_t_c_ha",
]