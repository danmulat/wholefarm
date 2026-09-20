"""Biophysical allocation and cohort aggregation from the pinned FAO GLEAM source."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence
from typing import Literal

import pandas as pd

from .gleam_core import _cohort, _fraction, _nonnegative, _species

GLEAM_FEED_EMISSION_SOURCES = (
    "co2_ration_fertilizer",
    "co2_ration_pesticides",
    "co2_ration_crop_activities",
    "co2_ration_luc_nopeat",
    "co2_ration_luc_peat",
    "n2o_ration_fertilizer",
    "n2o_ration_manure_applied",
    "n2o_ration_crop_residues",
    "ch4_ration_rice",
)

GLEAM_NON_ALLOCATED_EMISSION_SOURCES = (
    "ch4_manure_pasture",
    "ch4_manure_burned",
    "n2o_manure_pasture_direct",
    "n2o_manure_burned_direct",
    "n2o_manure_burned_indirect",
    "n2o_manure_pasture_indirect",
)


@dataclass(frozen=True)
class AllocationShares:
    meat: float
    milk: float
    fibre: float
    work: float
    eggs: float

    @property
    def total(self) -> float:
        return self.meat + self.milk + self.fibre + self.work + self.eggs


def calc_milk_allocation_energy(
    milk_production_fpcm_cohort: float,
    milk_protein_fraction_standard: float = 0.033,
    milk_fat_fraction_standard: float = 0.04,
    milk_lactose_fraction_standard: float = 0.048,
) -> float:
    for value, name in (
        (milk_production_fpcm_cohort, "milk_production_fpcm_cohort"),
        (milk_protein_fraction_standard, "milk_protein_fraction_standard"),
        (milk_fat_fraction_standard, "milk_fat_fraction_standard"),
        (milk_lactose_fraction_standard, "milk_lactose_fraction_standard"),
    ):
        _nonnegative(value, name)

    energy_standard_mj_kg = (
        0.0929 * milk_fat_fraction_standard
        + 0.0547 * milk_protein_fraction_standard
        + 0.0395 * milk_lactose_fraction_standard
    ) * 4.184 * 100.0
    return energy_standard_mj_kg * milk_production_fpcm_cohort


def calc_meat_allocation_energy(
    species_short: str,
    cohort_short: str,
    meat_production_live_weight_cohort: float,
    live_weight_cohort_at_slaughter: float | None = None,
    live_weight_at_birth: float | None = None,
    ratio_me_to_ne: float | None = None,
) -> float:
    _species(species_short)
    _cohort(cohort_short)
    _nonnegative(meat_production_live_weight_cohort, "meat_production_live_weight_cohort")

    if species_short == "PGS":
        return 0.0
    if live_weight_cohort_at_slaughter is None or live_weight_at_birth is None:
        raise ValueError("Live weights are required for meat allocation")
    if live_weight_cohort_at_slaughter <= 0:
        raise ValueError("Slaughter weight must be positive")
    _nonnegative(live_weight_at_birth, "live_weight_at_birth")

    if species_short in ("CTL", "BFL"):
        growth_efficiency_factor = 0.8 if cohort_short.startswith("F") else 1.0
        weight_gain = live_weight_cohort_at_slaughter - live_weight_at_birth
        if weight_gain < 0:
            raise ValueError("Slaughter weight cannot be below birth weight")
        specific_energy = (
            22.02
            * (
                (weight_gain / 2.0)
                / (growth_efficiency_factor * live_weight_cohort_at_slaughter)
            )
            ** 0.75
            * weight_gain**1.097
        ) / live_weight_cohort_at_slaughter
    elif species_short == "CML":
        if ratio_me_to_ne is None or ratio_me_to_ne <= 0:
            raise ValueError("ratio_me_to_ne must be positive for camels")
        specific_energy = (
            41.8
            * (live_weight_cohort_at_slaughter - live_weight_at_birth)
            / live_weight_cohort_at_slaughter
        ) / ratio_me_to_ne
    elif species_short == "SHP":
        a, b = (2.1, 0.45) if cohort_short.startswith("F") else (4.4, 0.32)
        specific_energy = (
            (live_weight_cohort_at_slaughter - live_weight_at_birth)
            * (
                a
                + 0.5
                * b
                * (live_weight_at_birth + live_weight_cohort_at_slaughter)
            )
        ) / live_weight_cohort_at_slaughter
    elif species_short == "GTS":
        a, b = 5.0, 0.33
        specific_energy = (
            (live_weight_cohort_at_slaughter - live_weight_at_birth)
            * (
                a
                + 0.5
                * b
                * (live_weight_at_birth + live_weight_cohort_at_slaughter)
            )
        ) / live_weight_cohort_at_slaughter
    else:
        raise ValueError("Unsupported species")

    return specific_energy * meat_production_live_weight_cohort


def calc_fibre_allocation_energy(
    species_short: str,
    cohort_stock_size: float,
    metabolic_energy_req_fibre_production: float,
    simulation_duration: float,
    ratio_me_to_ne: float | None = None,
) -> float:
    _species(species_short)
    for value, name in (
        (cohort_stock_size, "cohort_stock_size"),
        (metabolic_energy_req_fibre_production, "metabolic_energy_req_fibre_production"),
        (simulation_duration, "simulation_duration"),
    ):
        _nonnegative(value, name)

    energy = (
        metabolic_energy_req_fibre_production
        * simulation_duration
        * cohort_stock_size
    )
    if species_short in ("SHP", "GTS"):
        return energy
    if species_short == "CML":
        if ratio_me_to_ne is None or ratio_me_to_ne <= 0:
            raise ValueError("ratio_me_to_ne must be positive for camels")
        return energy / ratio_me_to_ne
    return 0.0


def calc_work_allocation_energy(
    species_short: str,
    cohort_stock_size: float,
    metabolic_energy_req_work: float,
    simulation_duration: float,
    ratio_me_to_ne: float | None = None,
) -> float:
    _species(species_short)
    for value, name in (
        (cohort_stock_size, "cohort_stock_size"),
        (metabolic_energy_req_work, "metabolic_energy_req_work"),
        (simulation_duration, "simulation_duration"),
    ):
        _nonnegative(value, name)

    energy = metabolic_energy_req_work * simulation_duration * cohort_stock_size
    if species_short == "CML":
        if ratio_me_to_ne is None or ratio_me_to_ne <= 0:
            raise ValueError("ratio_me_to_ne must be positive for camels")
        return energy / ratio_me_to_ne
    return energy


def calc_allocation_shares(
    species_short: str,
    meat_allocation_energy: float,
    milk_allocation_energy: float,
    fibre_allocation_energy: float,
    work_allocation_energy: float,
    egg_allocation_energy: float = 0.0,
) -> AllocationShares:
    _species(species_short)
    energies = (
        meat_allocation_energy,
        milk_allocation_energy,
        fibre_allocation_energy,
        work_allocation_energy,
        egg_allocation_energy,
    )
    for index, value in enumerate(energies):
        _nonnegative(value, f"allocation_energy_{index}")

    if species_short == "PGS":
        return AllocationShares(1.0, 0.0, 0.0, 0.0, 0.0)

    total = sum(energies)
    if total <= 0:
        raise ValueError("Total allocation energy must be positive")
    return AllocationShares(*(value / total for value in energies))


def calc_allocated_emissions(value: float, allocation_share: float) -> float:
    _nonnegative(value, "value")
    _fraction(allocation_share, "allocation_share")
    return value * allocation_share


def allocation_share_for_emission(
    source: str,
    commodity: Literal["Milk", "Meat", "Fibre", "Work", "Eggs", "Other"],
    shares: AllocationShares,
) -> float:
    if source in GLEAM_NON_ALLOCATED_EMISSION_SOURCES:
        return 1.0 if commodity == "Other" else 0.0
    if commodity == "Other":
        return 0.0
    mapping = {
        "Milk": shares.milk,
        "Meat": shares.meat,
        "Fibre": shares.fibre,
        "Work": shares.work,
        "Eggs": shares.eggs,
    }
    return mapping[commodity]


def calc_cohort_total(
    value: float,
    cohort_stock_size: float,
    ration_intake: float,
    simulation_duration: float,
    variable_name: str,
    variable_type: Literal["Production", "Emissions", "Feed", "NitrogenBalance"],
) -> float:
    _nonnegative(value, "value")
    _nonnegative(cohort_stock_size, "cohort_stock_size")
    _nonnegative(ration_intake, "ration_intake")
    _nonnegative(simulation_duration, "simulation_duration")

    if variable_type == "Production":
        return value
    if variable_name in GLEAM_FEED_EMISSION_SOURCES:
        return (
            value
            * ration_intake
            * cohort_stock_size
            * simulation_duration
            / 1000.0
        )
    return value * cohort_stock_size * simulation_duration


def calc_cohort_to_herd_aggregation(
    data_cohort: pd.DataFrame,
    id_cols: Sequence[str],
    vars_to_sum: Sequence[str],
    cohort_short: str | None = None,
) -> pd.DataFrame:
    """Aggregate cohort rows to herd totals as in the pinned GLEAM core model."""

    _ = cohort_short
    missing = set(id_cols).union(vars_to_sum).difference(data_cohort.columns)
    if missing:
        raise ValueError(f"Missing aggregation columns: {sorted(missing)}")
    if not id_cols:
        raise ValueError("At least one herd identifier column is required")
    if not vars_to_sum:
        raise ValueError("At least one variable must be aggregated")

    return (
        data_cohort.groupby(list(id_cols), dropna=False, as_index=False)[list(vars_to_sum)]
        .sum()
    )


def assign_allocation_shares(
    allocation_herd_long: pd.DataFrame,
    emissions_vars: Sequence[str],
    commodities: Sequence[str],
    non_allocated_emission_sources: Sequence[str],
    commodity_col: str = "commodity_name",
    allocation_col: str = "allocation_share",
) -> pd.DataFrame:
    """Expand commodity shares across emission sources and apply GLEAM exclusions."""

    if commodity_col not in allocation_herd_long.columns:
        raise ValueError(f"Missing commodity column: {commodity_col}")
    if allocation_col not in allocation_herd_long.columns:
        raise ValueError(f"Missing allocation column: {allocation_col}")
    if not emissions_vars:
        raise ValueError("At least one emission variable is required")
    if not commodities:
        raise ValueError("At least one commodity is required")

    commodity_values = set(allocation_herd_long[commodity_col].astype(str))
    requested_commodities = set(str(value) for value in commodities)
    missing_commodities = requested_commodities.difference(commodity_values)
    if missing_commodities:
        raise ValueError(
            f"Allocation table is missing commodities: {sorted(missing_commodities)}"
        )

    grid = pd.MultiIndex.from_product(
        [list(emissions_vars), list(commodities)],
        names=["variable_name", commodity_col],
    ).to_frame(index=False)

    expanded = allocation_herd_long.merge(
        grid,
        how="inner",
        on=commodity_col,
        validate="many_to_many",
    )
    non_allocated = set(non_allocated_emission_sources)
    is_non_allocated = expanded["variable_name"].isin(non_allocated)
    is_other = expanded[commodity_col].astype(str).eq("Other")

    expanded.loc[is_non_allocated & is_other, allocation_col] = 1.0
    expanded.loc[is_non_allocated & ~is_other, allocation_col] = 0.0
    expanded.loc[~is_non_allocated & is_other, allocation_col] = 0.0
    return expanded
