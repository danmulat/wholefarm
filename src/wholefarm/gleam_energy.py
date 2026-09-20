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

    _fraction(low_activity_fraction, "low_activity_fraction")
    _fraction(high_activity_fraction, "high_activity_fraction")

    if species_short in ("CTL", "BFL"):
        coefficient = (
            0.17 * low_activity_fraction
            + 0.36 * high_activity_fraction
        )
        return coefficient * metabolic_energy_req_maintenance
    if species_short == "CML":
        coefficient = 0.1 * (low_activity_fraction + high_activity_fraction)
        return coefficient * metabolic_energy_req_maintenance
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
        coefficient = 0.125 * (low_activity_fraction + high_activity_fraction)
        return coefficient * metabolic_energy_req_maintenance
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


def calc_metabolic_energy_req_growth(
    species_short: str,
    cohort_short: str,
    live_weight_cohort_average: float | None = None,
    live_weight_cohort_final: float | None = None,
    live_weight_cohort_initial: float | None = None,
    live_weight_mature_stage: float | None = None,
    daily_weight_gain: float | None = None,
    offtake_rate: float | None = None,
    cohort_duration_days: float | None = None,
) -> float:
    """Calculate daily growth energy using the pinned GLEAM equations."""

    _species(species_short)
    _cohort(cohort_short)
    growing = cohort_short in ("FS", "FJ", "MS", "MJ")
    if not growing:
        return 0.0

    if daily_weight_gain is None:
        raise ValueError("daily_weight_gain is required")
    _nonnegative(daily_weight_gain, "daily_weight_gain")

    if species_short in ("CTL", "BFL"):
        if live_weight_cohort_average is None or live_weight_mature_stage is None:
            raise ValueError("Average and mature weights are required")
        _nonnegative(live_weight_cohort_average, "live_weight_cohort_average")
        if live_weight_mature_stage <= 0:
            raise ValueError("live_weight_mature_stage must be positive")
        if cohort_short in ("FS", "FJ"):
            cgro = 0.8
        else:
            if offtake_rate is None:
                raise ValueError("offtake_rate is required for male growing cohorts")
            _fraction(offtake_rate, "offtake_rate")
            cgro = 1.2 * (1.0 - offtake_rate) + offtake_rate
        return (
            22.02
            * (live_weight_cohort_average / (cgro * live_weight_mature_stage)) ** 0.75
            * daily_weight_gain**1.097
        )

    if species_short == "CML":
        return 41.2 * daily_weight_gain

    if species_short in ("SHP", "GTS"):
        if (
            live_weight_cohort_final is None
            or live_weight_cohort_initial is None
            or cohort_duration_days is None
        ):
            raise ValueError("Initial weight, final weight, and cohort duration are required")
        _nonnegative(live_weight_cohort_initial, "live_weight_cohort_initial")
        _nonnegative(live_weight_cohort_final, "live_weight_cohort_final")
        if cohort_duration_days <= 0:
            raise ValueError("cohort_duration_days must be positive")
        if live_weight_cohort_final < live_weight_cohort_initial:
            raise ValueError("Final weight cannot be below initial weight")

        if species_short == "SHP":
            if cohort_short in ("FS", "FJ"):
                a, b = 2.1, 0.45
            else:
                if offtake_rate is None:
                    raise ValueError("offtake_rate is required for male growing sheep")
                _fraction(offtake_rate, "offtake_rate")
                a = 4.4 * offtake_rate + 2.5 * (1.0 - offtake_rate)
                b = 0.32 * offtake_rate + 0.35 * (1.0 - offtake_rate)
        else:
            a, b = 5.0, 0.33

        return (
            (live_weight_cohort_final - live_weight_cohort_initial)
            * (
                a
                + 0.5
                * b
                * (live_weight_cohort_initial + live_weight_cohort_final)
            )
            / cohort_duration_days
        )

    if species_short == "PGS":
        protein_tissue_fraction = 0.65
        cgro = (
            protein_tissue_fraction * 0.23 * 54.0
            + (1.0 - protein_tissue_fraction) * 0.9 * 52.3
        )
        return daily_weight_gain * cgro

    raise ValueError("unsupported species")


def calc_metabolic_energy_req_lactation(
    species_short: str,
    cohort_short: str,
    lactating_females_fraction: float | None = None,
    milk_yield_day: float | None = None,
    milk_fat_fraction: float | None = None,
    non_productive_duration: float | None = None,
    pregnancy_duration: float | None = None,
    litter_size: float | None = None,
    death_rate_juvenile: float | None = None,
    live_weight_at_birth: float | None = None,
    live_weight_at_weaning: float | None = None,
    lactation_duration: float | None = None,
    parturition_rate: float | None = None,
) -> float:
    """Calculate daily lactation energy using the pinned GLEAM equations."""

    _species(species_short)
    _cohort(cohort_short)
    if cohort_short != "FA":
        return 0.0

    if species_short in ("CTL", "BFL", "CML", "SHP", "GTS"):
        required = {
            "lactating_females_fraction": lactating_females_fraction,
            "milk_yield_day": milk_yield_day,
            "live_weight_at_birth": live_weight_at_birth,
            "live_weight_at_weaning": live_weight_at_weaning,
            "parturition_rate": parturition_rate,
        }
        if any(value is None for value in required.values()):
            raise ValueError(f"Missing lactation inputs: {required}")
        _fraction(lactating_females_fraction, "lactating_females_fraction")
        for value, name in (
            (milk_yield_day, "milk_yield_day"),
            (live_weight_at_birth, "live_weight_at_birth"),
            (live_weight_at_weaning, "live_weight_at_weaning"),
            (parturition_rate, "parturition_rate"),
        ):
            _nonnegative(value, name)
        if live_weight_at_weaning < live_weight_at_birth:
            raise ValueError("Weaning weight cannot be below birth weight")

        offspring_milk = (
            parturition_rate
            * 5.0
            * (live_weight_at_weaning - live_weight_at_birth)
            / 365.0
        )
        human_milk = milk_yield_day * lactating_females_fraction

        if species_short in ("CTL", "BFL"):
            if milk_fat_fraction is None:
                raise ValueError("milk_fat_fraction is required")
            _fraction(milk_fat_fraction, "milk_fat_fraction")
            energy_milk = milk_fat_fraction * 100.0 * 0.40 + 1.47
            return (human_milk + offspring_milk) * energy_milk
        if species_short == "CML":
            return (human_milk + offspring_milk) * 4.063

        if litter_size is None:
            raise ValueError("litter_size is required")
        _nonnegative(litter_size, "litter_size")
        offspring_milk *= litter_size
        energy_milk = 4.6 if species_short == "SHP" else 3.0
        return (human_milk + offspring_milk) * energy_milk

    if species_short == "PGS":
        required = {
            "non_productive_duration": non_productive_duration,
            "pregnancy_duration": pregnancy_duration,
            "litter_size": litter_size,
            "death_rate_juvenile": death_rate_juvenile,
            "live_weight_at_birth": live_weight_at_birth,
            "live_weight_at_weaning": live_weight_at_weaning,
            "lactation_duration": lactation_duration,
        }
        if any(value is None for value in required.values()):
            raise ValueError(f"Missing pig lactation inputs: {required}")
        for value, name in (
            (non_productive_duration, "non_productive_duration"),
            (pregnancy_duration, "pregnancy_duration"),
            (litter_size, "litter_size"),
            (live_weight_at_birth, "live_weight_at_birth"),
            (live_weight_at_weaning, "live_weight_at_weaning"),
        ):
            _nonnegative(value, name)
        _fraction(death_rate_juvenile, "death_rate_juvenile")
        if lactation_duration <= 0:
            raise ValueError("lactation_duration must be positive")
        cycle = non_productive_duration + pregnancy_duration + lactation_duration
        if cycle <= 0:
            raise ValueError("Reproductive cycle duration must be positive")
        cadj = lactation_duration / cycle
        return (
            litter_size
            * (1.0 - 0.5 * death_rate_juvenile)
            * (
                0.02059
                * (live_weight_at_weaning - live_weight_at_birth)
                * 1000.0
                / lactation_duration
                - 0.3766 / 0.67
            )
            * cadj
        )

    raise ValueError("unsupported species")


def calc_metabolic_energy_req_pregnancy(
    species_short: str,
    cohort_short: str,
    metabolic_energy_req_maintenance: float | None = None,
    parturition_rate: float | None = None,
    litter_size: float | None = None,
    pregnancy_duration: float | None = None,
    non_productive_duration: float | None = None,
    lactation_duration: float | None = None,
    cohort_duration_days: float | None = None,
    offtake_rate: float | None = None,
) -> float:
    """Calculate daily pregnancy energy using the pinned GLEAM equations."""

    _species(species_short)
    _cohort(cohort_short)
    if cohort_short not in ("FA", "FS"):
        return 0.0

    if species_short in ("CTL", "BFL", "CML", "SHP", "GTS"):
        if metabolic_energy_req_maintenance is None or pregnancy_duration is None:
            raise ValueError("Maintenance and pregnancy duration are required")
        _nonnegative(
            metabolic_energy_req_maintenance,
            "metabolic_energy_req_maintenance",
        )
        _nonnegative(pregnancy_duration, "pregnancy_duration")

    if cohort_short == "FS":
        if cohort_duration_days is None or cohort_duration_days <= 0:
            raise ValueError("cohort_duration_days must be positive")
        if offtake_rate is None:
            raise ValueError("offtake_rate is required")
        _fraction(offtake_rate, "offtake_rate")

    if species_short in ("CTL", "BFL"):
        if cohort_short == "FA":
            if parturition_rate is None:
                raise ValueError("parturition_rate is required")
            _nonnegative(parturition_rate, "parturition_rate")
            return (
                metabolic_energy_req_maintenance
                * 0.1
                * parturition_rate
                * pregnancy_duration
                / 365.0
            )
        return (
            metabolic_energy_req_maintenance
            * 0.1
            * (pregnancy_duration / cohort_duration_days)
            * (1.0 - offtake_rate)
        )

    if species_short == "CML":
        if cohort_short == "FA":
            if parturition_rate is None:
                raise ValueError("parturition_rate is required")
            _nonnegative(parturition_rate, "parturition_rate")
            return metabolic_energy_req_maintenance * 0.12 * parturition_rate
        return (
            metabolic_energy_req_maintenance
            * 0.12
            * (pregnancy_duration / cohort_duration_days)
            * (1.0 - offtake_rate)
        )

    if species_short in ("SHP", "GTS"):
        if cohort_short == "FA":
            if litter_size is None or parturition_rate is None:
                raise ValueError("litter_size and parturition_rate are required")
            _nonnegative(litter_size, "litter_size")
            _nonnegative(parturition_rate, "parturition_rate")
            if 1.0 <= litter_size <= 2.0:
                cpreg = 0.077 * (2.0 - litter_size) + 0.126 * (litter_size - 1.0)
            elif litter_size > 2.0:
                cpreg = 0.150
            else:
                cpreg = 0.0
            return (
                metabolic_energy_req_maintenance
                * cpreg
                * parturition_rate
                * pregnancy_duration
                / 365.0
            )
        return (
            metabolic_energy_req_maintenance
            * 0.077
            * (pregnancy_duration / cohort_duration_days)
            * (1.0 - offtake_rate)
        )

    if species_short == "PGS":
        if litter_size is None or pregnancy_duration is None:
            raise ValueError("litter_size and pregnancy_duration are required")
        _nonnegative(litter_size, "litter_size")
        _nonnegative(pregnancy_duration, "pregnancy_duration")
        cgest = 0.14985
        if cohort_short == "FA":
            if non_productive_duration is None or lactation_duration is None:
                raise ValueError("Pig reproductive cycle durations are required")
            _nonnegative(non_productive_duration, "non_productive_duration")
            _nonnegative(lactation_duration, "lactation_duration")
            denominator = (
                non_productive_duration + pregnancy_duration + lactation_duration
            )
            if denominator <= 0:
                raise ValueError("Pig reproductive cycle duration must be positive")
            return cgest * litter_size * pregnancy_duration / denominator
        return (
            cgest
            * litter_size
            * (pregnancy_duration / cohort_duration_days)
            * (1.0 - offtake_rate)
        )

    raise ValueError("unsupported species")


def calc_metabolic_energy_req_eggs(
    species_short: str,
    cohort_short: str,
    egg_yield_year: float | None = None,
    egg_average_weight: float | None = None,
) -> float:
    """Match the pinned GLEAM placeholder for egg production energy.

    The pinned FAO source returns NA for every supported input because egg energy
    is not implemented for the six livestock species currently supported.
    """

    _species(species_short)
    _cohort(cohort_short)
    _ = egg_yield_year, egg_average_weight
    return float("nan")
