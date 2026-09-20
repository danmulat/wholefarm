"""Scenario builders connecting explicit carbon flows to the RothC process model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .rothc import RothCMonth, RothCPools, annual_soc_trajectory, run_months


@dataclass(frozen=True)
class MonthlyClimate:
    temperature_c: float
    rainfall_mm: float
    open_pan_evaporation_mm: float
    plant_cover: int

    def __post_init__(self) -> None:
        if self.rainfall_mm < 0 or self.open_pan_evaporation_mm < 0:
            raise ValueError("Rainfall and evaporation must be nonnegative")
        if self.plant_cover not in (0, 1):
            raise ValueError("plant_cover must be zero or one")


@dataclass(frozen=True)
class RothCScenarioResult:
    initial_soc_t_c_ha: float
    final_soc_t_c_ha: float
    annual_soc_t_c_ha: tuple[float, ...]
    stock_change_t_c_ha: float
    stock_change_co2e_t: float


def distribute_annual_carbon(
    annual_carbon_t_ha: float,
    monthly_fractions: Sequence[float],
) -> tuple[float, ...]:
    if annual_carbon_t_ha < 0:
        raise ValueError("annual_carbon_t_ha must be nonnegative")
    if len(monthly_fractions) != 12:
        raise ValueError("monthly_fractions must contain twelve values")
    if any(value < 0 for value in monthly_fractions):
        raise ValueError("monthly fractions must be nonnegative")
    total = float(sum(monthly_fractions))
    if abs(total - 1.0) > 1e-9:
        raise ValueError("monthly fractions must sum to one")
    return tuple(annual_carbon_t_ha * value for value in monthly_fractions)


def build_rothc_year(
    climate: Sequence[MonthlyClimate],
    plant_c_t_ha_month: Sequence[float],
    manure_c_t_ha_month: Sequence[float],
    dpm_rpm_ratio: float,
) -> tuple[RothCMonth, ...]:
    if len(climate) != 12:
        raise ValueError("One RothC year requires twelve climate records")
    if len(plant_c_t_ha_month) != 12 or len(manure_c_t_ha_month) != 12:
        raise ValueError("Monthly carbon input sequences must contain twelve values")
    if dpm_rpm_ratio <= 0:
        raise ValueError("dpm_rpm_ratio must be positive")
    if any(value < 0 for value in plant_c_t_ha_month):
        raise ValueError("Plant carbon inputs must be nonnegative")
    if any(value < 0 for value in manure_c_t_ha_month):
        raise ValueError("Manure carbon inputs must be nonnegative")

    return tuple(
        RothCMonth(
            temperature_c=climate[index].temperature_c,
            rainfall_mm=climate[index].rainfall_mm,
            open_pan_evaporation_mm=climate[index].open_pan_evaporation_mm,
            plant_cover=climate[index].plant_cover,
            plant_c_input_t_ha=float(plant_c_t_ha_month[index]),
            fym_c_input_t_ha=float(manure_c_t_ha_month[index]),
            dpm_rpm_ratio=dpm_rpm_ratio,
        )
        for index in range(12)
    )


def repeat_rothc_year(
    year: Sequence[RothCMonth],
    years: int,
) -> tuple[RothCMonth, ...]:
    if len(year) != 12:
        raise ValueError("RothC year must contain twelve months")
    if years <= 0:
        raise ValueError("years must be positive")
    return tuple(year) * years


def run_rothc_scenario(
    initial_pools: RothCPools,
    months: Sequence[RothCMonth],
    clay_percent: float,
    depth_cm: float,
    area_ha: float,
) -> RothCScenarioResult:
    if depth_cm < 30.0:
        raise ValueError("Whole farm VM0042 SOC scenarios require at least 30 cm")
    if area_ha <= 0:
        raise ValueError("area_ha must be positive")
    if len(months) == 0 or len(months) % 12 != 0:
        raise ValueError("RothC scenario months must represent complete years")

    trajectory = annual_soc_trajectory(
        initial_pools,
        months,
        clay_percent,
        depth_cm,
    )
    final = trajectory[-1]
    change = final - initial_pools.total_soc
    return RothCScenarioResult(
        initial_soc_t_c_ha=initial_pools.total_soc,
        final_soc_t_c_ha=final,
        annual_soc_t_c_ha=tuple(trajectory),
        stock_change_t_c_ha=change,
        stock_change_co2e_t=change * area_ha * 44.0 / 12.0,
    )


def run_rothc_baseline_intervention(
    initial_pools: RothCPools,
    baseline_months: Sequence[RothCMonth],
    intervention_months: Sequence[RothCMonth],
    clay_percent: float,
    depth_cm: float,
    area_ha: float,
) -> tuple[RothCScenarioResult, RothCScenarioResult]:
    if len(baseline_months) != len(intervention_months):
        raise ValueError("Baseline and intervention must cover the same time period")
    baseline = run_rothc_scenario(
        initial_pools,
        baseline_months,
        clay_percent,
        depth_cm,
        area_ha,
    )
    intervention = run_rothc_scenario(
        initial_pools,
        intervention_months,
        clay_percent,
        depth_cm,
        area_ha,
    )
    return baseline, intervention
