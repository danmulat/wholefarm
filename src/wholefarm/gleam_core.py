"""Equation compatible livestock functions verified against the pinned FAO GLEAM source.

Reference repository: un-fao/GLEAM
Reference commit: 90e416197e89093c4f3a347b263ba805d33d4aac
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isnan

GLEAM_SPECIES = ("CTL", "BFL", "SHP", "GTS", "PGS", "CML")
GLEAM_COHORTS = ("FJ", "FS", "FA", "MJ", "MS", "MA")
GLEAM_MILK_PRODUCERS = ("CTL", "BFL", "SHP", "GTS", "CML")


def _species(value: str) -> None:
    if value not in GLEAM_SPECIES:
        raise ValueError(f"species_short must be one of {GLEAM_SPECIES}")


def _cohort(value: str) -> None:
    if value not in GLEAM_COHORTS:
        raise ValueError(f"cohort_short must be one of {GLEAM_COHORTS}")


def _fraction(value: float, name: str) -> None:
    if not 0 <= value <= 1:
        raise ValueError(f"{name} must be between zero and one")


def _nonnegative(value: float, name: str) -> None:
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")


def calc_feed_digestibility_fraction(
    feed_digestible_energy_ruminant: float | None,
    feed_digestible_energy_pigs: float | None,
    feed_gross_energy: float,
) -> dict[str, float]:
    if feed_gross_energy <= 0:
        raise ValueError("feed_gross_energy must be positive")
    ruminant = (
        0.0
        if feed_digestible_energy_ruminant is None or isnan(feed_digestible_energy_ruminant)
        else feed_digestible_energy_ruminant / feed_gross_energy
    )
    pigs = (
        0.0
        if feed_digestible_energy_pigs is None or isnan(feed_digestible_energy_pigs)
        else feed_digestible_energy_pigs / feed_gross_energy
    )
    return {
        "feed_digestibility_fraction_ruminant": float(ruminant),
        "feed_digestibility_fraction_pigs": float(pigs),
    }


def calc_ration_digestibility(
    species_short: str,
    feed_ration_fraction: float,
    feed_digestibility_fraction_ruminant: float | None = None,
    feed_digestibility_fraction_pigs: float | None = None,
) -> float:
    _species(species_short)
    _fraction(feed_ration_fraction, "feed_ration_fraction")
    if species_short in GLEAM_MILK_PRODUCERS:
        if feed_digestibility_fraction_ruminant is None:
            raise ValueError("ruminant digestibility is required")
        value = feed_digestibility_fraction_ruminant
    else:
        if feed_digestibility_fraction_pigs is None:
            raise ValueError("pig digestibility is required")
        value = feed_digestibility_fraction_pigs
    _fraction(value, "feed_digestibility_fraction")
    return feed_ration_fraction * value


def calc_ration_gross_energy(feed_ration_fraction: float, feed_gross_energy: float) -> float:
    _fraction(feed_ration_fraction, "feed_ration_fraction")
    _nonnegative(feed_gross_energy, "feed_gross_energy")
    return feed_ration_fraction * feed_gross_energy


def calc_ration_nitrogen_content(
    feed_ration_fraction: float,
    feed_nitrogen_content: float,
) -> float:
    _fraction(feed_ration_fraction, "feed_ration_fraction")
    _nonnegative(feed_nitrogen_content, "feed_nitrogen_content")
    return feed_ration_fraction * feed_nitrogen_content


def calc_ration_ash(feed_ration_fraction: float, feed_ash_percent: float) -> float:
    _fraction(feed_ration_fraction, "feed_ration_fraction")
    if not 0 <= feed_ash_percent <= 100:
        raise ValueError("feed_ash_percent must be between zero and one hundred")
    return feed_ration_fraction * feed_ash_percent / 100.0


def calc_conversion_factor_ym(
    species_short: str,
    cohort_short: str,
    ration_digestibility_fraction: float,
) -> float:
    _species(species_short)
    _cohort(cohort_short)
    _fraction(ration_digestibility_fraction, "ration_digestibility_fraction")

    if cohort_short in ("FJ", "MJ"):
        return 0.0
    if species_short in ("CTL", "BFL"):
        return 9.75 - 0.05 * ration_digestibility_fraction * 100.0
    if species_short in ("SHP", "GTS", "CML"):
        if cohort_short in ("FS", "MS"):
            return 7.75 - 0.05 * ration_digestibility_fraction * 100.0
        return 9.75 - 0.05 * ration_digestibility_fraction * 100.0
    if species_short == "PGS":
        return 0.39 if cohort_short in ("FS", "MS") else 1.01
    raise ValueError("unsupported species")


def calc_ch4_enteric(
    species_short: str,
    ch4_conversion_factor_ym: float,
    ch4_mitigation_factor: float,
    ration_gross_energy: float,
    ration_intake: float,
) -> float:
    _species(species_short)
    _nonnegative(ch4_conversion_factor_ym, "ch4_conversion_factor_ym")
    _nonnegative(ch4_mitigation_factor, "ch4_mitigation_factor")
    _nonnegative(ration_gross_energy, "ration_gross_energy")
    _nonnegative(ration_intake, "ration_intake")
    return (
        ration_gross_energy
        * ration_intake
        * (ch4_conversion_factor_ym / 100.0)
        * ch4_mitigation_factor
        / 55.65
    )


def calc_nitrogen_intake(ration_intake: float, ration_nitrogen: float) -> float:
    _nonnegative(ration_intake, "ration_intake")
    _nonnegative(ration_nitrogen, "ration_nitrogen")
    return ration_intake * ration_nitrogen


def calc_nitrogen_retention(
    species_short: str,
    cohort_short: str,
    milk_protein_fraction: float | None = None,
    milk_yield_day: float | None = None,
    daily_weight_gain: float | None = None,
    fibre_yield_year: float | None = None,
    litter_size: float | None = None,
    parturition_rate: float | None = None,
    live_weight_at_weaning: float | None = None,
    live_weight_at_birth: float | None = None,
    pregnancy_duration: float | None = None,
    cohort_duration_days: float | None = None,
) -> float:
    _species(species_short)
    _cohort(cohort_short)

    if species_short in GLEAM_MILK_PRODUCERS:
        tissue_n = 0.0326 if species_short in ("CTL", "BFL") else 0.026
        milk_component = 0.0
        growth_component = 0.0
        fibre_component = 0.0

        if cohort_short == "FA" and milk_yield_day is not None and milk_yield_day > 0:
            if milk_protein_fraction is None:
                raise ValueError("milk_protein_fraction is required for milk retention")
            milk_component = milk_yield_day * (milk_protein_fraction / 6.25)
        if daily_weight_gain is not None and daily_weight_gain > 0:
            growth_component = daily_weight_gain * tissue_n
        if (
            fibre_yield_year is not None
            and fibre_yield_year > 0
            and cohort_short in ("FA", "FS", "MA", "MS")
            and species_short in ("SHP", "GTS", "CML")
        ):
            fibre_component = fibre_yield_year / 365.0 * 0.134
        return milk_component + growth_component + fibre_component

    if species_short == "PGS":
        if cohort_short == "FA":
            required = [litter_size, parturition_rate, live_weight_at_weaning, live_weight_at_birth]
            if any(value is None for value in required):
                raise ValueError("pig adult female reproductive inputs are required")
            return (
                0.025
                * litter_size
                * parturition_rate
                * (live_weight_at_weaning - live_weight_at_birth)
                / 0.98
                + 0.025 * litter_size * parturition_rate * live_weight_at_birth
            ) / 365.0
        if cohort_short == "FS":
            required = [
                daily_weight_gain,
                litter_size,
                live_weight_at_birth,
                pregnancy_duration,
                cohort_duration_days,
            ]
            if any(value is None for value in required):
                raise ValueError("pig subadult female inputs are required")
            return 0.025 * daily_weight_gain + (
                0.025
                * litter_size
                * (pregnancy_duration / cohort_duration_days)
                * live_weight_at_birth
                / 0.806
            ) / 365.0
        if daily_weight_gain is None:
            raise ValueError("daily_weight_gain is required")
        return 0.025 * daily_weight_gain

    raise ValueError("unsupported species")


def calc_nitrogen_excretion(
    species_short: str,
    nitrogen_intake: float,
    nitrogen_retention: float,
) -> float:
    _species(species_short)
    _nonnegative(nitrogen_intake, "nitrogen_intake")
    _nonnegative(nitrogen_retention, "nitrogen_retention")
    if nitrogen_retention > nitrogen_intake:
        raise ValueError("nitrogen_intake must be greater than or equal to nitrogen_retention")
    return nitrogen_intake - nitrogen_retention


def calc_volatile_solids(
    ration_intake: float,
    ration_digestibility_fraction: float,
    ration_urinary_energy_fraction: float,
    ration_ash: float,
) -> float:
    _nonnegative(ration_intake, "ration_intake")
    _fraction(ration_digestibility_fraction, "ration_digestibility_fraction")
    _fraction(ration_urinary_energy_fraction, "ration_urinary_energy_fraction")
    _fraction(ration_ash, "ration_ash")
    return (
        ration_intake
        * (1.0 - ration_digestibility_fraction + ration_urinary_energy_fraction)
        * (1.0 - ration_ash)
    )


@dataclass(frozen=True)
class ManureManagementSystem:
    fraction: float
    methane_conversion_factor_percent: float = 0.0
    bo_m3_ch4_per_kg_vs: float = 0.0
    n2o_ef3: float = 0.0
    n2o_ef4: float = 0.0
    nitrogen_fracgas: float = 0.0
    n2o_ef5: float = 0.0
    nitrogen_fracleach: float = 0.0

    def __post_init__(self) -> None:
        _fraction(self.fraction, "fraction")
        if not 0 <= self.methane_conversion_factor_percent <= 100:
            raise ValueError("methane_conversion_factor_percent is invalid")
        _nonnegative(self.bo_m3_ch4_per_kg_vs, "bo_m3_ch4_per_kg_vs")
        _nonnegative(self.n2o_ef3, "n2o_ef3")
        _nonnegative(self.n2o_ef4, "n2o_ef4")
        _fraction(self.nitrogen_fracgas, "nitrogen_fracgas")
        _nonnegative(self.n2o_ef5, "n2o_ef5")
        _fraction(self.nitrogen_fracleach, "nitrogen_fracleach")


def _validate_mms(systems: dict[str, ManureManagementSystem]) -> None:
    if not systems:
        raise ValueError("At least one manure management system is required")
    total = sum(item.fraction for item in systems.values())
    if abs(total - 1.0) > 1e-9:
        raise ValueError("Manure management system fractions must sum to one")


def calc_ch4_manure(
    volatile_solids: float,
    systems: dict[str, ManureManagementSystem],
    methane_density_kg_m3: float = 0.67,
) -> dict[str, float]:
    _nonnegative(volatile_solids, "volatile_solids")
    _nonnegative(methane_density_kg_m3, "methane_density_kg_m3")
    _validate_mms(systems)

    def component(item: ManureManagementSystem) -> float:
        return (
            volatile_solids
            * methane_density_kg_m3
            * item.fraction
            * item.methane_conversion_factor_percent
            / 100.0
            * item.bo_m3_ch4_per_kg_vs
        )

    pasture = component(systems["mms_pasture"]) if "mms_pasture" in systems else 0.0
    burned = component(systems["mms_burned"]) if "mms_burned" in systems else 0.0
    other = sum(
        component(item)
        for name, item in systems.items()
        if name not in ("mms_pasture", "mms_burned")
    )
    return {
        "ch4_manure_pasture": pasture,
        "ch4_manure_burned": burned,
        "ch4_manure_other": other,
        "ch4_manure_all_noburn": pasture + other,
    }


def _n2o_by_group(
    nitrogen_excretion: float,
    systems: dict[str, ManureManagementSystem],
    factor,
    ratio_n2on_to_n2o: float = 44.0 / 28.0,
) -> dict[str, float]:
    _nonnegative(nitrogen_excretion, "nitrogen_excretion")
    _validate_mms(systems)

    def component(item: ManureManagementSystem) -> float:
        return nitrogen_excretion * ratio_n2on_to_n2o * item.fraction * factor(item)

    pasture = component(systems["mms_pasture"]) if "mms_pasture" in systems else 0.0
    burned = component(systems["mms_burned"]) if "mms_burned" in systems else 0.0
    other = sum(
        component(item)
        for name, item in systems.items()
        if name not in ("mms_pasture", "mms_burned")
    )
    return {"pasture": pasture, "burned": burned, "other": other, "all_noburn": pasture + other}


def calc_n2o_manure_direct(
    nitrogen_excretion: float,
    systems: dict[str, ManureManagementSystem],
) -> dict[str, float]:
    values = _n2o_by_group(nitrogen_excretion, systems, lambda item: item.n2o_ef3)
    return {
        "n2o_manure_pasture_direct": values["pasture"],
        "n2o_manure_burned_direct": values["burned"],
        "n2o_manure_other_direct": values["other"],
        "n2o_manure_all_noburn_direct": values["all_noburn"],
    }


def calc_n2o_manure_volatilization(
    nitrogen_excretion: float,
    systems: dict[str, ManureManagementSystem],
) -> dict[str, float]:
    values = _n2o_by_group(
        nitrogen_excretion,
        systems,
        lambda item: item.nitrogen_fracgas * item.n2o_ef4,
    )
    return {
        "n2o_manure_pasture_vol": values["pasture"],
        "n2o_manure_burned_vol": values["burned"],
        "n2o_manure_other_vol": values["other"],
        "n2o_manure_all_noburn_vol": values["all_noburn"],
    }


def calc_n2o_manure_leaching(
    nitrogen_excretion: float,
    systems: dict[str, ManureManagementSystem],
) -> dict[str, float]:
    values = _n2o_by_group(
        nitrogen_excretion,
        systems,
        lambda item: item.nitrogen_fracleach * item.n2o_ef5,
    )
    return {
        "n2o_manure_pasture_leach": values["pasture"],
        "n2o_manure_burned_leach": values["burned"],
        "n2o_manure_other_leach": values["other"],
        "n2o_manure_all_noburn_leach": values["all_noburn"],
    }


@dataclass(frozen=True)
class MilkProduction:
    mass_kg: float
    protein_kg: float
    fpcm_kg: float


def calc_milk_production(
    species_short: str,
    cohort_short: str,
    milk_yield_day: float,
    simulation_duration: float,
    cohort_stock_size: float,
    lactating_females_fraction: float,
    milk_protein_fraction: float,
    milk_fat_fraction: float,
    milk_lactose_fraction: float,
    milk_protein_fraction_standard: float = 0.033,
    milk_fat_fraction_standard: float = 0.04,
    milk_lactose_fraction_standard: float = 0.048,
) -> MilkProduction:
    _species(species_short)
    _cohort(cohort_short)
    if species_short not in GLEAM_MILK_PRODUCERS or cohort_short != "FA":
        return MilkProduction(0.0, 0.0, 0.0)
    _fraction(lactating_females_fraction, "lactating_females_fraction")
    energy_standard = (
        0.0929 * milk_fat_fraction_standard
        + 0.0547 * milk_protein_fraction_standard
        + 0.0395 * milk_lactose_fraction_standard
    )
    energy_milk = (
        0.0929 * milk_fat_fraction
        + 0.0547 * milk_protein_fraction
        + 0.0395 * milk_lactose_fraction
    )
    mass = milk_yield_day * simulation_duration * cohort_stock_size * lactating_females_fraction
    protein = mass * milk_protein_fraction
    fpcm = mass * energy_milk / energy_standard
    return MilkProduction(mass, protein, fpcm)


@dataclass(frozen=True)
class MeatProduction:
    live_weight_kg: float
    carcass_weight_kg: float
    bone_free_meat_kg: float
    protein_kg: float


def calc_meat_production(
    offtake_heads_assessment: float,
    live_weight_cohort_at_slaughter: float,
    carcass_dressing_fraction: float,
    bone_free_meat_fraction: float,
    meat_protein_fraction: float,
) -> MeatProduction:
    live_weight = offtake_heads_assessment * live_weight_cohort_at_slaughter
    carcass = live_weight * carcass_dressing_fraction
    bone_free = carcass * bone_free_meat_fraction
    protein = bone_free * meat_protein_fraction
    return MeatProduction(live_weight, carcass, bone_free, protein)
