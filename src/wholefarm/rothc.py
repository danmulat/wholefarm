"""RothC carbon pool core adapted from the pinned Rothamsted Python implementation.

Reference repository: Rothamsted-Models/RothC_Py
Pinned commit: bd90ce3cf616d5316042b73a3b1f09c5b6e3b361

The implementation here retains the carbon pool equations and monthly rate
modifiers while exposing them as reusable library functions. Radiocarbon age
tracking from the reference script is intentionally outside this first module.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from math import exp

ROTHC_PINNED_COMMIT = "bd90ce3cf616d5316042b73a3b1f09c5b6e3b361"


@dataclass(frozen=True)
class RothCPools:
    dpm: float
    rpm: float
    bio: float
    hum: float
    iom: float

    def __post_init__(self) -> None:
        for value in (self.dpm, self.rpm, self.bio, self.hum, self.iom):
            if value < 0:
                raise ValueError("RothC carbon pools cannot be negative")

    @property
    def active_soc(self) -> float:
        return self.dpm + self.rpm + self.bio + self.hum

    @property
    def total_soc(self) -> float:
        return self.active_soc + self.iom


@dataclass(frozen=True)
class RothCMonth:
    temperature_c: float
    rainfall_mm: float
    open_pan_evaporation_mm: float
    plant_cover: int
    plant_c_input_t_ha: float
    fym_c_input_t_ha: float
    dpm_rpm_ratio: float

    def __post_init__(self) -> None:
        if self.rainfall_mm < 0 or self.open_pan_evaporation_mm < 0:
            raise ValueError("Rainfall and evaporation must be nonnegative")
        if self.plant_cover not in (0, 1):
            raise ValueError("plant_cover must be zero or one")
        if self.plant_c_input_t_ha < 0 or self.fym_c_input_t_ha < 0:
            raise ValueError("Carbon inputs must be nonnegative")
        if self.dpm_rpm_ratio <= 0:
            raise ValueError("dpm_rpm_ratio must be positive")


@dataclass(frozen=True)
class RothCStepResult:
    pools: RothCPools
    soil_water_deficit_mm: float
    temperature_modifier: float
    moisture_modifier: float
    cover_modifier: float
    rate_modifier: float
    carbon_decomposed_t_ha: float
    carbon_to_co2_t_ha: float


def rmf_temperature(temperature_c: float) -> float:
    if temperature_c < -5.0:
        return 0.0
    return 47.91 / (exp(106.06 / (temperature_c + 18.27)) + 1.0)


def rmf_moisture(
    rainfall_mm: float,
    open_pan_evaporation_mm: float,
    clay_percent: float,
    depth_cm: float,
    plant_cover: int,
    soil_water_deficit_mm: float,
) -> tuple[float, float]:
    if not 0 <= clay_percent <= 100:
        raise ValueError("clay_percent must be between zero and one hundred")
    if depth_cm <= 0:
        raise ValueError("depth_cm must be positive")
    if rainfall_mm < 0 or open_pan_evaporation_mm < 0:
        raise ValueError("Rainfall and evaporation must be nonnegative")
    if plant_cover not in (0, 1):
        raise ValueError("plant_cover must be zero or one")

    smd_max = -(20.0 + 1.3 * clay_percent - 0.01 * clay_percent**2)
    smd_max_adjusted = smd_max * depth_cm / 23.0
    smd_one_bar = 0.444 * smd_max_adjusted
    smd_bare = 0.556 * smd_max_adjusted
    moisture_balance = rainfall_mm - 0.75 * open_pan_evaporation_mm

    swc_after_balance = min(0.0, soil_water_deficit_mm + moisture_balance)
    bare_limited_swc = min(smd_bare, soil_water_deficit_mm)

    if plant_cover == 1:
        new_swc = max(smd_max_adjusted, swc_after_balance)
    else:
        new_swc = max(bare_limited_swc, swc_after_balance)

    if new_swc > smd_one_bar:
        modifier = 1.0
    else:
        modifier = 0.2 + 0.8 * (
            (smd_max_adjusted - new_swc) / (smd_max_adjusted - smd_one_bar)
        )
    return modifier, new_swc


def rmf_plant_cover(plant_cover: int) -> float:
    if plant_cover == 0:
        return 1.0
    if plant_cover == 1:
        return 0.6
    raise ValueError("plant_cover must be zero or one")


def decompose(
    pools: RothCPools,
    clay_percent: float,
    rate_modifier: float,
    plant_c_input_t_ha: float,
    fym_c_input_t_ha: float,
    dpm_rpm_ratio: float,
    time_factor: float = 12.0,
) -> tuple[RothCPools, float, float]:
    if time_factor <= 0:
        raise ValueError("time_factor must be positive")
    if rate_modifier < 0:
        raise ValueError("rate_modifier must be nonnegative")
    if not 0 <= clay_percent <= 100:
        raise ValueError("clay_percent must be between zero and one hundred")
    if plant_c_input_t_ha < 0 or fym_c_input_t_ha < 0:
        raise ValueError("Carbon inputs must be nonnegative")
    if dpm_rpm_ratio <= 0:
        raise ValueError("dpm_rpm_ratio must be positive")

    step = 1.0 / time_factor
    rates = {"dpm": 10.0, "rpm": 0.3, "bio": 0.66, "hum": 0.02}
    initial = {
        "dpm": pools.dpm,
        "rpm": pools.rpm,
        "bio": pools.bio,
        "hum": pools.hum,
    }
    remaining = {
        name: value * exp(-rate_modifier * rates[name] * step)
        for name, value in initial.items()
    }
    decomposed = {name: initial[name] - remaining[name] for name in initial}

    x = 1.67 * (1.85 + 1.60 * exp(-0.0786 * clay_percent))
    to_co2_fraction = x / (x + 1.0)
    to_bio_fraction = 0.46 / (x + 1.0)
    to_hum_fraction = 0.54 / (x + 1.0)

    total_decomposed = sum(decomposed.values())
    carbon_to_co2 = total_decomposed * to_co2_fraction
    carbon_to_bio = total_decomposed * to_bio_fraction
    carbon_to_hum = total_decomposed * to_hum_fraction

    plant_dpm = dpm_rpm_ratio / (dpm_rpm_ratio + 1.0) * plant_c_input_t_ha
    plant_rpm = 1.0 / (dpm_rpm_ratio + 1.0) * plant_c_input_t_ha

    fym_dpm = 0.49 * fym_c_input_t_ha
    fym_rpm = 0.49 * fym_c_input_t_ha
    fym_hum = 0.02 * fym_c_input_t_ha

    new_pools = RothCPools(
        dpm=remaining["dpm"] + plant_dpm + fym_dpm,
        rpm=remaining["rpm"] + plant_rpm + fym_rpm,
        bio=remaining["bio"] + carbon_to_bio,
        hum=remaining["hum"] + carbon_to_hum + fym_hum,
        iom=pools.iom,
    )
    return new_pools, total_decomposed, carbon_to_co2


def step_month(
    pools: RothCPools,
    month: RothCMonth,
    clay_percent: float,
    depth_cm: float,
    soil_water_deficit_mm: float,
) -> RothCStepResult:
    temperature = rmf_temperature(month.temperature_c)
    moisture, new_swc = rmf_moisture(
        month.rainfall_mm,
        month.open_pan_evaporation_mm,
        clay_percent,
        depth_cm,
        month.plant_cover,
        soil_water_deficit_mm,
    )
    cover = rmf_plant_cover(month.plant_cover)
    rate = temperature * moisture * cover
    new_pools, decomposed, to_co2 = decompose(
        pools,
        clay_percent=clay_percent,
        rate_modifier=rate,
        plant_c_input_t_ha=month.plant_c_input_t_ha,
        fym_c_input_t_ha=month.fym_c_input_t_ha,
        dpm_rpm_ratio=month.dpm_rpm_ratio,
    )
    return RothCStepResult(
        new_pools,
        new_swc,
        temperature,
        moisture,
        cover,
        rate,
        decomposed,
        to_co2,
    )


def run_months(
    initial_pools: RothCPools,
    months: Sequence[RothCMonth],
    clay_percent: float,
    depth_cm: float,
    initial_soil_water_deficit_mm: float = 0.0,
) -> list[RothCStepResult]:
    pools = initial_pools
    swc = initial_soil_water_deficit_mm
    results = []
    for month in months:
        result = step_month(pools, month, clay_percent, depth_cm, swc)
        results.append(result)
        pools = result.pools
        swc = result.soil_water_deficit_mm
    return results


def spin_up(
    climate_cycle: Sequence[RothCMonth],
    clay_percent: float,
    depth_cm: float,
    iom_t_c_ha: float,
    tolerance_t_c_ha: float = 1e-6,
    max_years: int = 10000,
) -> RothCPools:
    if len(climate_cycle) != 12:
        raise ValueError("RothC spin up requires a twelve month climate and input cycle")
    if iom_t_c_ha < 0:
        raise ValueError("iom_t_c_ha must be nonnegative")
    if tolerance_t_c_ha <= 0 or max_years <= 0:
        raise ValueError("spin up controls must be positive")

    pools = RothCPools(0.0, 0.0, 0.0, 0.0, iom_t_c_ha)
    swc = 0.0
    previous_active = 0.0

    for _ in range(max_years):
        for month in climate_cycle:
            result = step_month(pools, month, clay_percent, depth_cm, swc)
            pools = result.pools
            swc = result.soil_water_deficit_mm
        difference = abs(pools.active_soc - previous_active)
        if difference <= tolerance_t_c_ha:
            return pools
        previous_active = pools.active_soc

    raise RuntimeError("RothC spin up did not converge within max_years")


def annual_soc_trajectory(
    initial_pools: RothCPools,
    months: Iterable[RothCMonth],
    clay_percent: float,
    depth_cm: float,
) -> list[float]:
    monthly = tuple(months)
    if len(monthly) % 12 != 0:
        raise ValueError("SOC trajectory requires a whole number of years")
    results = run_months(initial_pools, monthly, clay_percent, depth_cm)
    trajectory = [initial_pools.total_soc]
    for index in range(11, len(results), 12):
        trajectory.append(results[index].pools.total_soc)
    return trajectory