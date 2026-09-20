"""Farm level aggregation of cohort calculations from the pinned GLEAM chain."""

from __future__ import annotations

from dataclasses import dataclass

from .accounting import LivestockGHG
from .gleam_cohort import CohortInputs, GleamCohortResult, RationProfile, run_gleam_cohort
from .gleam_core import ManureManagementSystem


@dataclass(frozen=True)
class DietEmissionFactors:
    co2_fertilizer_g_kg_dm: float | None = None
    co2_pesticides_g_kg_dm: float | None = None
    co2_crop_activities_g_kg_dm: float | None = None
    co2_luc_nopeat_g_kg_dm: float | None = None
    co2_luc_peat_g_kg_dm: float | None = None
    n2o_fertilizer_g_kg_dm: float | None = None
    n2o_manure_applied_g_kg_dm: float | None = None
    n2o_crop_residues_g_kg_dm: float | None = None
    ch4_rice_g_kg_dm: float | None = None

    def __post_init__(self) -> None:
        for value in self.values:
            if value is not None and value < 0:
                raise ValueError("Feed emission factors must be nonnegative")

    @property
    def values(self) -> tuple[float | None, ...]:
        return (
            self.co2_fertilizer_g_kg_dm,
            self.co2_pesticides_g_kg_dm,
            self.co2_crop_activities_g_kg_dm,
            self.co2_luc_nopeat_g_kg_dm,
            self.co2_luc_peat_g_kg_dm,
            self.n2o_fertilizer_g_kg_dm,
            self.n2o_manure_applied_g_kg_dm,
            self.n2o_crop_residues_g_kg_dm,
            self.ch4_rice_g_kg_dm,
        )

    @property
    def complete(self) -> bool:
        return all(value is not None for value in self.values)


@dataclass(frozen=True)
class LivestockCohortSpec:
    inputs: CohortInputs
    ration: RationProfile
    manure_systems: dict[str, ManureManagementSystem]
    feed_emissions: DietEmissionFactors | None = None


@dataclass(frozen=True)
class FeedEmissionTotals:
    co2_kg: float
    n2o_kg: float
    ch4_kg: float
    co2e_t: float
    complete: bool


@dataclass(frozen=True)
class LivestockFarmResult:
    ghg: LivestockGHG
    enteric_ch4_kg: float
    manure_ch4_kg: float
    manure_n2o_kg: float
    feed_co2_kg: float
    feed_n2o_kg: float
    feed_ch4_kg: float
    nitrogen_intake_kg: float
    nitrogen_excretion_kg: float
    volatile_solids_kg: float
    milk_fpcm_kg: float
    meat_live_weight_kg: float
    meat_carcass_weight_kg: float
    fibre_kg: float
    feed_emission_profile_complete: bool
    cohort_results: tuple[GleamCohortResult, ...]


def _value(value: float | None) -> float:
    return 0.0 if value is None else value


def calculate_feed_emissions(
    dry_matter_intake_kg: float,
    factors: DietEmissionFactors | None,
    gwp_ch4: float,
    gwp_n2o: float,
) -> FeedEmissionTotals:
    if dry_matter_intake_kg < 0:
        raise ValueError("dry_matter_intake_kg must be nonnegative")
    if gwp_ch4 < 0 or gwp_n2o < 0:
        raise ValueError("Global warming potentials must be nonnegative")
    if factors is None:
        return FeedEmissionTotals(0.0, 0.0, 0.0, 0.0, False)

    co2_factor = sum(
        _value(value)
        for value in (
            factors.co2_fertilizer_g_kg_dm,
            factors.co2_pesticides_g_kg_dm,
            factors.co2_crop_activities_g_kg_dm,
            factors.co2_luc_nopeat_g_kg_dm,
            factors.co2_luc_peat_g_kg_dm,
        )
    )
    n2o_factor = sum(
        _value(value)
        for value in (
            factors.n2o_fertilizer_g_kg_dm,
            factors.n2o_manure_applied_g_kg_dm,
            factors.n2o_crop_residues_g_kg_dm,
        )
    )
    ch4_factor = _value(factors.ch4_rice_g_kg_dm)

    co2_kg = dry_matter_intake_kg * co2_factor / 1000.0
    n2o_kg = dry_matter_intake_kg * n2o_factor / 1000.0
    ch4_kg = dry_matter_intake_kg * ch4_factor / 1000.0
    co2e_t = (co2_kg + n2o_kg * gwp_n2o + ch4_kg * gwp_ch4) / 1000.0
    return FeedEmissionTotals(co2_kg, n2o_kg, ch4_kg, co2e_t, factors.complete)


def run_livestock_farm(
    cohorts: list[LivestockCohortSpec],
    gwp_ch4: float = 27.2,
    gwp_n2o: float = 273.0,
) -> LivestockFarmResult:
    if not cohorts:
        raise ValueError("At least one livestock cohort is required")
    if gwp_ch4 < 0 or gwp_n2o < 0:
        raise ValueError("Global warming potentials must be nonnegative")

    results: list[GleamCohortResult] = []
    enteric_ch4 = 0.0
    manure_ch4 = 0.0
    manure_n2o = 0.0
    feed_co2 = 0.0
    feed_n2o = 0.0
    feed_ch4 = 0.0
    feed_co2e = 0.0
    nitrogen_intake = 0.0
    nitrogen_excretion = 0.0
    volatile_solids = 0.0
    milk_fpcm = 0.0
    meat_live_weight = 0.0
    meat_carcass_weight = 0.0
    fibre = 0.0
    feed_complete = True

    for spec in cohorts:
        result = run_gleam_cohort(spec.inputs, spec.ration, spec.manure_systems)
        results.append(result)
        exposure = spec.inputs.cohort_stock_size * spec.inputs.simulation_duration_days
        dry_matter_intake = result.ration_intake_kg_dm_head_day * exposure
        feed = calculate_feed_emissions(
            dry_matter_intake,
            spec.feed_emissions,
            gwp_ch4,
            gwp_n2o,
        )

        enteric_ch4 += result.totals.enteric_ch4_kg
        manure_ch4 += result.totals.manure_ch4_kg
        manure_n2o += result.totals.manure_n2o_kg
        feed_co2 += feed.co2_kg
        feed_n2o += feed.n2o_kg
        feed_ch4 += feed.ch4_kg
        feed_co2e += feed.co2e_t
        nitrogen_intake += result.totals.nitrogen_intake_kg
        nitrogen_excretion += result.totals.nitrogen_excretion_kg
        volatile_solids += result.emissions.volatile_solids_kg_head_day * exposure
        milk_fpcm += result.production.milk.fpcm_kg
        meat_live_weight += result.production.meat.live_weight_kg
        meat_carcass_weight += result.production.meat.carcass_weight_kg
        fibre += result.production.fibre_kg
        feed_complete = feed_complete and feed.complete

    ghg = LivestockGHG(
        enteric_ch4_co2e_t=enteric_ch4 / 1000.0 * gwp_ch4,
        manure_ch4_co2e_t=manure_ch4 / 1000.0 * gwp_ch4,
        manure_n2o_co2e_t=manure_n2o / 1000.0 * gwp_n2o,
        feed_production_co2e_t=feed_co2e,
    )
    return LivestockFarmResult(
        ghg=ghg,
        enteric_ch4_kg=enteric_ch4,
        manure_ch4_kg=manure_ch4,
        manure_n2o_kg=manure_n2o,
        feed_co2_kg=feed_co2,
        feed_n2o_kg=feed_n2o,
        feed_ch4_kg=feed_ch4,
        nitrogen_intake_kg=nitrogen_intake,
        nitrogen_excretion_kg=nitrogen_excretion,
        volatile_solids_kg=volatile_solids,
        milk_fpcm_kg=milk_fpcm,
        meat_live_weight_kg=meat_live_weight,
        meat_carcass_weight_kg=meat_carcass_weight,
        fibre_kg=fibre,
        feed_emission_profile_complete=feed_complete,
        cohort_results=tuple(results),
    )
