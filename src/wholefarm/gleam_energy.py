"""Selected energy requirement equations ported from the pinned FAO GLEAM source.

This module implements the weight dependent maintenance requirement, REM, REG,
total energy aggregation, and dry matter intake calculation. Other GLEAM energy
partitions are added separately so incomplete inputs cannot be hidden.
"""

from __future__ import annotations

from math import isnan

from .gleam_core import _cohort, _fraction, _nonnegative, _species

NET_ENERGY_SPECIES = ("CTL", "BFL", "SHP", "GTS")


def calc_metabolic_energy_req_maintenance(
    species_short: str,
    cohort_short: str,
    live_weight_cohort_average: float,
    lactating_females_fraction: float | None = None,
    offtake_rate: float | None = None,
    age_first_parturition: float | None = None,
) -> float:
    _species(species_short)
    _cohort(cohort_short)
    _nonnegative(live_weight_cohort_average, "live_weight_cohort_average")

    if species_short in ("CTL", "BFL"):
        if cohort_short == "FA":
            if lactating_females_fraction is None:
                raise ValueError("lactating_females_fraction is required")
            _fraction(lactating_females_fraction, "lactating_females_fraction")
            cmain = (
                0.386 * lactating_females_fraction
                + 0.322 * (1.0 - lactating_females_fraction)
            )
        elif cohort_short in ("MA", "MS"):
            if offtake_rate is None:
                raise ValueError("offtake_rate is required")
            _fraction(offtake_rate, "offtake_rate")
            cmain = 0.322 * offtake_rate + 0.370 * (1.0 - offtake_rate)
        else:
            cmain = 0.322
    elif species_short == "CML":
        cmain = 0.435
    elif species_short == "GTS":
        cmain = 0.315
    elif species_short == "SHP":
        if cohort_short == "FA":
            cmain = 0.217
        elif cohort_short == "FJ":
            cmain = 0.236
        elif cohort_short == "FS":
            if age_first_parturition is None or age_first_parturition <= 0:
                raise ValueError("age_first_parturition is required and must be positive")
            cmain = (
                0.236 * (365.0 / age_first_parturition)
                + 0.217 * ((age_first_parturition - 365.0) / age_first_parturition)
            )
        elif cohort_short == "MA":
            if offtake_rate is None:
                raise ValueError("offtake_rate is required")
            _fraction(offtake_rate, "offtake_rate")
            cmain = 0.217 * offtake_rate + (0.217 * 1.15) * (1.0 - offtake_rate)
        elif cohort_short == "MJ":
            if offtake_rate is None:
                raise ValueError("offtake_rate is required")
            _fraction(offtake_rate, "offtake_rate")
            cmain = 0.236 * offtake_rate + (0.236 * 1.15) * (1.0 - offtake_rate)
        else:
            if offtake_rate is None:
                raise ValueError("offtake_rate is required")
            if age_first_parturition is None or age_first_parturition <= 0:
                raise ValueError("age_first_parturition is required and must be positive")
            _fraction(offtake_rate, "offtake_rate")
            adult = 0.217 * offtake_rate + (0.217 * 1.15) * (1.0 - offtake_rate)
            juvenile = 0.236 * offtake_rate + (0.236 * 1.15) * (1.0 - offtake_rate)
            cmain = (
                adult * ((age_first_parturition - 365.0) / age_first_parturition)
                + juvenile * (365.0 / age_first_parturition)
            )
    elif species_short == "PGS":
        cmain = 0.4435
    else:
        raise ValueError("unsupported species")

    return cmain * live_weight_cohort_average**0.75


def calc_rem_maintenance(
    species_short: str,
    ration_digestibility_fraction: float | None = None,
) -> float | None:
    _species(species_short)
    if species_short not in NET_ENERGY_SPECIES:
        return None
    if ration_digestibility_fraction is None or isnan(ration_digestibility_fraction):
        raise ValueError("ration_digestibility_fraction is required")
    _fraction(ration_digestibility_fraction, "ration_digestibility_fraction")
    de = ration_digestibility_fraction * 100.0
    if de == 0:
        raise ValueError("ration_digestibility_fraction must be greater than zero")
    return 1.123 - 0.004092 * de + 0.00001126 * de**2 - 25.4 / de


def calc_reg_growth(
    species_short: str,
    ration_digestibility_fraction: float | None = None,
) -> float | None:
    _species(species_short)
    if species_short not in NET_ENERGY_SPECIES:
        return None
    if ration_digestibility_fraction is None or isnan(ration_digestibility_fraction):
        raise ValueError("ration_digestibility_fraction is required")
    _fraction(ration_digestibility_fraction, "ration_digestibility_fraction")
    de = ration_digestibility_fraction * 100.0
    if de == 0:
        raise ValueError("ration_digestibility_fraction must be greater than zero")
    return 1.164 - 0.005160 * de + 0.00001308 * de**2 - 37.4 / de


def calc_total_metabolic_energy_req(
    species_short: str,
    metabolic_energy_req_maintenance: float,
    metabolic_energy_req_activity: float,
    metabolic_energy_req_lactation: float,
    metabolic_energy_req_work: float,
    metabolic_energy_req_pregnancy: float,
    net_energy_maintenance_digestible_energy_ratio: float | None,
    metabolic_energy_req_growth: float,
    metabolic_energy_req_fibre_production: float,
    metabolic_energy_req_egg_deposition: float,
    net_energy_growth_digestible_energy_ratio: float | None,
    ration_digestibility_fraction: float,
) -> float:
    _species(species_short)
    values = (
        metabolic_energy_req_maintenance,
        metabolic_energy_req_activity,
        metabolic_energy_req_lactation,
        metabolic_energy_req_work,
        metabolic_energy_req_pregnancy,
        metabolic_energy_req_growth,
        metabolic_energy_req_fibre_production,
        metabolic_energy_req_egg_deposition,
    )
    for index, value in enumerate(values):
        _nonnegative(value, f"energy_component_{index}")

    if species_short in NET_ENERGY_SPECIES:
        _fraction(ration_digestibility_fraction, "ration_digestibility_fraction")
        if ration_digestibility_fraction == 0:
            raise ValueError("ration_digestibility_fraction must be greater than zero")
        if (
            net_energy_maintenance_digestible_energy_ratio is None
            or net_energy_growth_digestible_energy_ratio is None
        ):
            raise ValueError("REM and REG are required for net energy species")
        rem = net_energy_maintenance_digestible_energy_ratio
        reg = net_energy_growth_digestible_energy_ratio
        if rem <= 0 or reg <= 0:
            raise ValueError("REM and REG must be positive")

        if species_short in ("CTL", "BFL"):
            maintenance_group = (
                metabolic_energy_req_maintenance
                + metabolic_energy_req_activity
                + metabolic_energy_req_lactation
                + metabolic_energy_req_work
                + metabolic_energy_req_pregnancy
            )
            growth_group = metabolic_energy_req_growth
        else:
            maintenance_group = (
                metabolic_energy_req_maintenance
                + metabolic_energy_req_activity
                + metabolic_energy_req_lactation
                + metabolic_energy_req_pregnancy
            )
            growth_group = (
                metabolic_energy_req_growth + metabolic_energy_req_fibre_production
            )
        return (maintenance_group / rem + growth_group / reg) / ration_digestibility_fraction

    if species_short == "CML":
        return (
            metabolic_energy_req_maintenance
            + metabolic_energy_req_activity
            + metabolic_energy_req_lactation
            + metabolic_energy_req_work
            + metabolic_energy_req_fibre_production
            + metabolic_energy_req_pregnancy
            + metabolic_energy_req_growth
        )

    if species_short == "PGS":
        return (
            metabolic_energy_req_maintenance
            + metabolic_energy_req_activity
            + metabolic_energy_req_lactation
            + metabolic_energy_req_pregnancy
            + metabolic_energy_req_growth
        )

    raise ValueError("unsupported species")


def calc_ration_intake(
    species_short: str,
    metabolic_energy_req_total: float,
    ration_gross_energy: float,
    ration_metabolizable_energy: float,
) -> float:
    _species(species_short)
    _nonnegative(metabolic_energy_req_total, "metabolic_energy_req_total")
    if species_short in NET_ENERGY_SPECIES:
        if ration_gross_energy <= 0:
            raise ValueError("ration_gross_energy must be positive")
        return metabolic_energy_req_total / ration_gross_energy
    if ration_metabolizable_energy <= 0:
        raise ValueError("ration_metabolizable_energy must be positive")
    return metabolic_energy_req_total / ration_metabolizable_energy


def calc_metabolic_energy_req_activity(
    species_short: str,
    cohort_short: str,
    metabolic_energy_req_maintenance: float,
    live_weight_cohort_average: float,
    low_activity_fraction: float = 0.0,
    high_activity_fraction: float = 0.0,
) -> float:
    """Calculate daily activity energy following the pinned GLEAM rules."""

    _species(species_short)
    _cohort(cohort_short)
    _nonnegative(
        metabolic_energy_req_maintenance,
        "metabolic_energy_req_maintenance",
    )
    _nonnegative(live_weight_cohort_average, "live_weight_cohort_average")

    if species_short in ("CTL", "BFL", "SHP", "GTS"):
        _fraction(low_activity_fraction, "low_activity_fraction")
        _fraction(high_activity_fraction, "high_activity_fraction")
        if abs(low_activity_fraction + high_activity_fraction - 1.0) > 1e-9:
            raise ValueError("Low and high activity fractions must sum to one")

    if species_short in ("CTL", "BFL"):
        coefficient = (
            0.17 * low_activity_fraction
            + 0.36 * high_activity_fraction
        )
        return coefficient * metabolic_energy_req_maintenance
    if species_short == "CML":
        return 0.1 * metabolic_energy_req_maintenance
    if species_short == "GTS":
        coefficient = (
            0.019 * low_activity_fraction
            + 0.024 * high_activity_fraction
        )
        return coefficient * live_weight_cohort_average
    if species_short == "SHP":
        coefficient = (
            0.0107 * low_activity_fraction
            + 0.024 * high_activity_fraction
        )
        return coefficient * live_weight_cohort_average
    if species_short == "PGS":
        return 0.125 * metabolic_energy_req_maintenance
    raise ValueError("unsupported species")


def calc_metabolic_energy_req_work(
    species_short: str,
    cohort_short: str,
    metabolic_energy_req_maintenance: float,
    draught_work_hours_female: float = 0.0,
    draught_work_hours_male: float = 0.0,
    draught_fraction_female: float = 0.0,
    draught_fraction_male: float = 0.0,
) -> float:
    """Calculate daily draught work energy for adult cattle, buffalo, and camels."""

    _species(species_short)
    _cohort(cohort_short)
    _nonnegative(
        metabolic_energy_req_maintenance,
        "metabolic_energy_req_maintenance",
    )

    if species_short not in ("CTL", "BFL", "CML"):
        return 0.0
    if cohort_short not in ("FA", "MA"):
        return 0.0

    if cohort_short == "FA":
        hours = draught_work_hours_female
        fraction = draught_fraction_female
    else:
        hours = draught_work_hours_male
        fraction = draught_fraction_male

    _nonnegative(hours, "draught_work_hours")
    _fraction(fraction, "draught_fraction")

    if species_short in ("CTL", "BFL"):
        return 0.1 * metabolic_energy_req_maintenance * hours * fraction
    return 4.0 * hours * fraction


def calc_metabolic_energy_req_fibre(
    species_short: str,
    cohort_short: str,
    fibre_yield_year: float = 0.0,
) -> float:
    """Calculate daily fibre production energy from the pinned GLEAM source."""

    _species(species_short)
    _cohort(cohort_short)
    _nonnegative(fibre_yield_year, "fibre_yield_year")

    if cohort_short not in ("FA", "FS", "MA", "MS"):
        return 0.0
    if species_short in ("SHP", "GTS"):
        return 24.0 * fibre_yield_year / 365.0
    if species_short == "CML":
        return (24.0 / 0.43) * fibre_yield_year / 365.0
    return 0.0
