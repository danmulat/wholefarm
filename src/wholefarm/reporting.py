"""Structured farm reporting for scientific, CAP2ER and CARBON AGRI views."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .accounting import FarmScenarioResult, ScenarioComparison
from .cap2er import NitrogenIndicators
from .cap2er_level2 import IndicatorValue, merge_level2_results
from .carbon_agri import CarbonAgriGain


@dataclass(frozen=True)
class ScenarioGHGSummary:
    scenario_name: str
    gross_ghg_t_co2e: float
    soil_removals_t_co2e: float
    tree_removals_t_co2e: float
    total_removals_t_co2e: float
    net_ghg_t_co2e: float
    milk_fpcm_kg: float | None
    meat_live_weight_kg: float | None
    milk_intensity_kg_co2e_per_kg_fpcm: float | None


@dataclass(frozen=True)
class ComparisonSummary:
    baseline: ScenarioGHGSummary
    intervention: ScenarioGHGSummary
    gross_emission_reduction_t_co2e: float
    additional_removals_t_co2e: float
    total_climate_benefit_t_co2e: float


def _optional_production(
    scenario: FarmScenarioResult,
    name: str,
) -> float | None:
    value = scenario.production.get(name)
    if value is None:
        return None
    return float(value)


def summarize_scenario(scenario: FarmScenarioResult) -> ScenarioGHGSummary:
    milk = _optional_production(scenario, "milk_fpcm_kg")
    meat = _optional_production(scenario, "meat_live_weight_kg")
    milk_intensity = None
    if milk is not None and milk > 0:
        milk_intensity = scenario.emissions.gross_co2e_t * 1000.0 / milk

    return ScenarioGHGSummary(
        scenario_name=scenario.scenario_name,
        gross_ghg_t_co2e=scenario.emissions.gross_co2e_t,
        soil_removals_t_co2e=scenario.removals.soil_co2e_t,
        tree_removals_t_co2e=scenario.removals.tree_biomass_co2e_t,
        total_removals_t_co2e=scenario.removals.total_removals_co2e_t,
        net_ghg_t_co2e=scenario.net_co2e_t,
        milk_fpcm_kg=milk,
        meat_live_weight_kg=meat,
        milk_intensity_kg_co2e_per_kg_fpcm=milk_intensity,
    )


def summarize_comparison(comparison: ScenarioComparison) -> ComparisonSummary:
    return ComparisonSummary(
        baseline=summarize_scenario(comparison.baseline),
        intervention=summarize_scenario(comparison.intervention),
        gross_emission_reduction_t_co2e=comparison.gross_emission_reduction_co2e_t,
        additional_removals_t_co2e=comparison.additional_removals_co2e_t,
        total_climate_benefit_t_co2e=comparison.total_climate_benefit_co2e_t,
    )


def cap2er_level2_report(
    scenario: FarmScenarioResult,
    nitrogen: NitrogenIndicators | None = None,
) -> dict[str, IndicatorValue]:
    computed: dict[str, IndicatorValue] = {
        "GHG emissions": IndicatorValue(
            name="GHG emissions",
            category="climate_change",
            value=scenario.emissions.gross_co2e_t,
            unit="t_CO2e",
            status="computed",
            source_note="whole_farm_scientific_inventory",
        ),
        "Carbon storage": IndicatorValue(
            name="Carbon storage",
            category="carbon_storage",
            value=scenario.removals.total_removals_co2e_t,
            unit="t_CO2e",
            status="computed",
            source_note="soil_and_tree_stock_change",
        ),
    }
    if nitrogen is not None:
        computed["Nitrogen balance"] = IndicatorValue(
            name="Nitrogen balance",
            category="nitrogen",
            value=nitrogen.apparent_balance_kg_n_ha,
            unit="kg_N_ha",
            status="computed",
            source_note="CAP2ER_public_equation",
        )
        computed["Nitrogen efficiency"] = IndicatorValue(
            name="Nitrogen efficiency",
            category="nitrogen",
            value=nitrogen.efficiency_fraction,
            unit="fraction",
            status="computed",
            source_note="CAP2ER_public_equation",
        )
        computed["Leaching"] = IndicatorValue(
            name="Leaching",
            category="air_water_quality",
            value=nitrogen.leaching_potential_kg_n_ha,
            unit="kg_N_ha",
            status="computed",
            source_note="CAP2ER_public_equation",
        )
    return merge_level2_results(computed)


def carbon_agri_report(
    gain: CarbonAgriGain,
    project_years: int,
    methodology_version: str = "31 July 2019",
) -> dict[str, float | int | str]:
    if not 1 <= project_years <= 5:
        raise ValueError("CARBON AGRI project duration must be between one and five years")
    return {
        "methodology": "CARBON AGRI",
        "methodology_version": methodology_version,
        "project_years": project_years,
        "footprint_gain_kg_co2e": gain.footprint_gain_kg_co2e,
        "sequestration_gain_kg_co2e": gain.sequestration_gain_kg_co2e,
        "farm_carbon_gain_kg_co2e": gain.farm_carbon_gain_kg_co2e,
    }


def report_to_dict(report: object) -> dict:
    if not hasattr(report, "__dataclass_fields__"):
        raise TypeError("report_to_dict expects a dataclass report")
    return asdict(report)
