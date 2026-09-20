"""Cohort weight calculations ported from the pinned FAO GLEAM source."""

from __future__ import annotations

from dataclasses import dataclass

from .gleam_core import GLEAM_COHORTS, _cohort, _fraction, _nonnegative


@dataclass(frozen=True)
class CohortWeights:
    live_weight_mature_stage: float
    live_weight_cohort_initial: float
    live_weight_cohort_potential_final: float
    live_weight_cohort_at_slaughter: float


@dataclass(frozen=True)
class AverageWeights:
    live_weight_cohort_average: float
    live_weight_cohort_final: float


def calc_cohort_weights(
    cohort_short: str,
    live_weight_female_adult: float,
    live_weight_male_adult: float,
    live_weight_at_birth: float,
    live_weight_female_at_slaughter: float,
    live_weight_male_at_slaughter: float,
    live_weight_at_weaning: float,
) -> CohortWeights:
    _cohort(cohort_short)
    for value, name in (
        (live_weight_female_adult, "live_weight_female_adult"),
        (live_weight_male_adult, "live_weight_male_adult"),
        (live_weight_at_birth, "live_weight_at_birth"),
        (live_weight_female_at_slaughter, "live_weight_female_at_slaughter"),
        (live_weight_male_at_slaughter, "live_weight_male_at_slaughter"),
        (live_weight_at_weaning, "live_weight_at_weaning"),
    ):
        _nonnegative(value, name)

    if cohort_short in ("FJ", "MJ"):
        initial = live_weight_at_birth
        potential = live_weight_at_weaning
        slaughter = live_weight_at_weaning
        mature = live_weight_female_adult if cohort_short == "FJ" else live_weight_male_adult
    elif cohort_short in ("FS", "MS"):
        initial = live_weight_at_weaning
        if cohort_short == "FS":
            mature = live_weight_female_adult
            slaughter = live_weight_female_at_slaughter
        else:
            mature = live_weight_male_adult
            slaughter = live_weight_male_at_slaughter
        potential = mature
    elif cohort_short == "FA":
        initial = live_weight_female_adult
        mature = live_weight_female_adult
        potential = mature
        slaughter = mature
    elif cohort_short == "MA":
        initial = live_weight_male_adult
        mature = live_weight_male_adult
        potential = mature
        slaughter = mature
    else:
        raise ValueError(f"cohort_short must be one of {GLEAM_COHORTS}")

    return CohortWeights(mature, initial, potential, slaughter)


def calc_avg_weights(
    live_weight_cohort_initial: float,
    live_weight_cohort_potential_final: float,
    live_weight_cohort_at_slaughter: float,
    offtake_rate: float,
) -> AverageWeights:
    for value, name in (
        (live_weight_cohort_initial, "live_weight_cohort_initial"),
        (live_weight_cohort_potential_final, "live_weight_cohort_potential_final"),
        (live_weight_cohort_at_slaughter, "live_weight_cohort_at_slaughter"),
    ):
        _nonnegative(value, name)
    _fraction(offtake_rate, "offtake_rate")

    final = (
        live_weight_cohort_potential_final * (1.0 - offtake_rate)
        + live_weight_cohort_at_slaughter * offtake_rate
    )
    average = (live_weight_cohort_initial + final) / 2.0
    return AverageWeights(average, final)


def calc_daily_weight_gain(
    live_weight_cohort_potential_final: float,
    live_weight_cohort_initial: float,
    cohort_duration_days: float,
) -> float:
    _nonnegative(live_weight_cohort_potential_final, "live_weight_cohort_potential_final")
    _nonnegative(live_weight_cohort_initial, "live_weight_cohort_initial")
    if cohort_duration_days <= 0:
        raise ValueError("cohort_duration_days must be positive")
    return (
        live_weight_cohort_potential_final - live_weight_cohort_initial
    ) / cohort_duration_days
