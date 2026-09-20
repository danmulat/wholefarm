"""Herd demography functions ported from the pinned FAO GLEAM source."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, log

import numpy as np

CORE_COHORTS = ("FJ", "FS", "FA", "MJ", "MS", "MA")
TEN_COHORTS = ("FB", "FJ", "FS", "FA", "FC", "MB", "MJ", "MS", "MA", "MC")


@dataclass(frozen=True)
class FecundityRates:
    fecundity_female: float
    fecundity_male: float


@dataclass(frozen=True)
class TransitionProbabilities:
    hazard_death: dict[str, float]
    hazard_offtake: dict[str, float]
    probability_death: dict[str, float]
    probability_offtake: dict[str, float]
    probability_survival: dict[str, float]
    probability_growth: dict[str, float]


@dataclass(frozen=True)
class SteadyStateStructure:
    days_to_steady_state: int
    herd_structure: dict[str, float]
    cohort_share: dict[str, float]
    growth_rate_herd: float


@dataclass(frozen=True)
class ProjectedPopulation:
    cohort_stock_start: dict[str, float]
    cohort_stock_end_projected: dict[str, float]
    cohort_stock_end_exact_simulated: dict[str, float]
    cohort_stock_average: dict[str, float]
    cohort_offtake_heads: dict[str, float]


def _require_keys(values: dict[str, float], required: tuple[str, ...], name: str) -> None:
    missing = [key for key in required if key not in values]
    if missing:
        raise ValueError(f"{name} is missing keys: {missing}")


def calc_fecundity_rates(
    parturition_rate: float,
    litter_size: float,
    birth_fraction_female: float,
) -> FecundityRates:
    if parturition_rate < 0 or litter_size < 0:
        raise ValueError("parturition_rate and litter_size must be nonnegative")
    if not 0 <= birth_fraction_female <= 1:
        raise ValueError("birth_fraction_female must be between zero and one")
    female = litter_size * birth_fraction_female * (parturition_rate / 365.0)
    male = litter_size * (1.0 - birth_fraction_female) * (parturition_rate / 365.0)
    return FecundityRates(female, male)


def calc_transition_probabilities(
    cohort_duration_days: dict[str, float],
    offtake_rate: dict[str, float],
    death_rate: dict[str, float],
) -> TransitionProbabilities:
    for values, name in (
        (cohort_duration_days, "cohort_duration_days"),
        (offtake_rate, "offtake_rate"),
        (death_rate, "death_rate"),
    ):
        _require_keys(values, CORE_COHORTS, name)

    durations = dict(cohort_duration_days)
    off = dict(offtake_rate)
    death = dict(death_rate)
    for cohort in CORE_COHORTS:
        if durations[cohort] <= 1:
            raise ValueError("cohort durations must exceed one day")
        if not 0 <= off[cohort] < 1 or not 0 <= death[cohort] < 1:
            raise ValueError("offtake and death rates must be in the interval zero to one")
        if off[cohort] == 0 and death[cohort] == 0:
            death[cohort] = 1e-12

    hazard_death = {}
    duration_max365 = {}
    hazard_offtake = {}

    for cohort in CORE_COHORTS:
        duration = durations[cohort]
        denominator = duration if duration < 365 else 365.0
        hazard_death[cohort] = -log(1.0 - death[cohort]) / denominator
        duration_max365[cohort] = denominator

        hazard_death_adj = hazard_death[cohort] * denominator
        class_hazard_offtake = off[cohort]
        for _ in range(15):
            total = hazard_death_adj + class_hazard_offtake
            class_f = (
                class_hazard_offtake / total
                * (1.0 - exp(-total))
                - off[cohort]
            )
            class_deriv = (
                hazard_death_adj * (1.0 - exp(-total))
                + class_hazard_offtake * total * exp(-total)
            ) / total**2
            class_hazard_offtake -= class_f / class_deriv
        hazard_offtake[cohort] = class_hazard_offtake / denominator

    hazard_death_all = {
        "FB": hazard_death["FJ"],
        "FJ": hazard_death["FJ"],
        "FS": hazard_death["FS"],
        "FA": hazard_death["FA"],
        "FC": hazard_death["FA"],
        "MB": hazard_death["MJ"],
        "MJ": hazard_death["MJ"],
        "MS": hazard_death["MS"],
        "MA": hazard_death["MA"],
        "MC": hazard_death["MA"],
    }
    hazard_offtake_all = {
        "FB": hazard_offtake["FJ"],
        "FJ": hazard_offtake["FJ"],
        "FS": hazard_offtake["FS"],
        "FA": hazard_offtake["FA"],
        "FC": hazard_offtake["FA"],
        "MB": hazard_offtake["MJ"],
        "MJ": hazard_offtake["MJ"],
        "MS": hazard_offtake["MS"],
        "MA": hazard_offtake["MA"],
        "MC": hazard_offtake["MA"],
    }
    duration_all = {
        "FB": 1.0,
        "FJ": durations["FJ"] - 1.0,
        "FS": durations["FS"],
        "FA": durations["FA"],
        "FC": 1.0,
        "MB": 1.0,
        "MJ": durations["MJ"] - 1.0,
        "MS": durations["MS"],
        "MA": durations["MA"],
        "MC": 1.0,
    }

    probability_death = {}
    probability_offtake = {}
    probability_survival = {}
    probability_growth = {}

    for cohort in TEN_COHORTS:
        hd = hazard_death_all[cohort]
        ho = hazard_offtake_all[cohort]
        total = hd + ho
        probability_death[cohort] = hd / total * (1.0 - exp(-total))
        probability_offtake[cohort] = ho / total * (1.0 - exp(-total))

    probability_death["FC"] = 0.0
    probability_death["MC"] = 0.0
    probability_offtake["FC"] = 1.0
    probability_offtake["MC"] = 1.0

    for cohort in TEN_COHORTS:
        survival = 1.0 - probability_death[cohort] - probability_offtake[cohort]
        probability_survival[cohort] = survival
        duration = duration_all[cohort]
        denominator = 1.0 - survival**duration
        if denominator == 0:
            probability_growth[cohort] = 0.0
        else:
            probability_growth[cohort] = (
                survival ** (duration - 1.0) - survival**duration
            ) / denominator

    return TransitionProbabilities(
        hazard_death,
        hazard_offtake,
        probability_death,
        probability_offtake,
        probability_survival,
        probability_growth,
    )


def calc_steady_state_structure(
    initial_herd_structure: dict[str, float],
    max_simulation_years: int,
    min_lambda_change: float,
    fecundity_female: float,
    fecundity_male: float,
    probability_death: dict[str, float],
    probability_offtake: dict[str, float],
    probability_growth: dict[str, float],
) -> SteadyStateStructure:
    _require_keys(initial_herd_structure, CORE_COHORTS, "initial_herd_structure")
    for values, name in (
        (probability_death, "probability_death"),
        (probability_offtake, "probability_offtake"),
        (probability_growth, "probability_growth"),
    ):
        _require_keys(values, TEN_COHORTS, name)
    if max_simulation_years <= 0 or min_lambda_change <= 0:
        raise ValueError("simulation controls must be positive")

    state = {key: float(initial_herd_structure[key]) for key in CORE_COHORTS}
    previous = None
    previous_previous = None
    days_steady = 1
    birth_female = state["FA"] * fecundity_female
    birth_male = state["FA"] * fecundity_male

    max_days = max_simulation_years * 365 + 1
    for day in range(1, max_days + 1):
        if day > 1:
            birth_female = state["FA"] * fecundity_female
            birth_male = state["FA"] * fecundity_male

        if previous is not None and previous_previous is not None:
            lambda_change = []
            for cohort in CORE_COHORTS:
                a = state[cohort]
                b = previous[cohort]
                c = previous_previous[cohort]
                if b == 0 or c == 0:
                    lambda_change.append(float("inf"))
                else:
                    lambda_change.append(a / b - b / c)
            if all(value < min_lambda_change for value in lambda_change):
                days_steady = day
                break

        survived = {}
        for cohort in CORE_COHORTS:
            survived[cohort] = state[cohort] * (
                1.0 - probability_death[cohort] - probability_offtake[cohort]
            )

        next_state = {
            "FJ": birth_female
            * (1.0 - probability_death["FB"] - probability_offtake["FB"])
            + (1.0 - probability_growth["FJ"]) * survived["FJ"],
            "FS": probability_growth["FJ"] * survived["FJ"]
            + (1.0 - probability_growth["FS"]) * survived["FS"],
            "FA": probability_growth["FS"] * survived["FS"]
            + (1.0 - probability_growth["FA"]) * survived["FA"],
            "MJ": birth_male
            * (1.0 - probability_death["MB"] - probability_offtake["MB"])
            + (1.0 - probability_growth["MJ"]) * survived["MJ"],
            "MS": probability_growth["MJ"] * survived["MJ"]
            + (1.0 - probability_growth["MS"]) * survived["MS"],
            "MA": probability_growth["MS"] * survived["MS"]
            + (1.0 - probability_growth["MA"]) * survived["MA"],
        }

        previous_previous = previous
        previous = dict(state)
        state = next_state
        days_steady = day

    birth_female = state["FA"] * fecundity_female
    birth_male = state["FA"] * fecundity_male
    eight = {
        "FB": birth_female,
        "FJ": state["FJ"],
        "FS": state["FS"],
        "FA": state["FA"],
        "MB": birth_male,
        "MJ": state["MJ"],
        "MS": state["MS"],
        "MA": state["MA"],
    }
    total = sum(eight.values())
    if total <= 0:
        raise ValueError("steady state simulation produced an empty herd")
    structure = {key: value / total for key, value in eight.items()}
    share = {
        "FJ": structure["FB"] + structure["FJ"],
        "FS": structure["FS"],
        "FA": structure["FA"],
        "MJ": structure["MB"] + structure["MJ"],
        "MS": structure["MS"],
        "MA": structure["MA"],
    }

    if previous is None or previous["FJ"] == 0:
        growth_rate = 0.0
    else:
        growth_rate = (state["FJ"] / previous["FJ"]) ** 365 - 1.0
    return SteadyStateStructure(days_steady, structure, share, growth_rate)


def calc_projected_population_size(
    herd_size_total: float,
    fecundity_female: float,
    fecundity_male: float,
    probability_death: dict[str, float],
    probability_offtake: dict[str, float],
    probability_growth: dict[str, float],
    growth_rate_herd: float,
    herd_structure: dict[str, float],
    cohort_share: dict[str, float],
) -> ProjectedPopulation:
    if herd_size_total < 0:
        raise ValueError("herd_size_total must be nonnegative")
    _require_keys(herd_structure, ("FB", "FJ", "FS", "FA", "MB", "MJ", "MS", "MA"), "herd_structure")
    _require_keys(cohort_share, CORE_COHORTS, "cohort_share")
    for values, name in (
        (probability_death, "probability_death"),
        (probability_offtake, "probability_offtake"),
        (probability_growth, "probability_growth"),
    ):
        _require_keys(values, TEN_COHORTS, name)

    xini = {key: herd_size_total * value for key, value in herd_structure.items()}
    stock_start = {key: herd_size_total * cohort_share[key] for key in CORE_COHORTS}
    stock_end = {key: (1.0 + growth_rate_herd) * value for key, value in stock_start.items()}
    stock_average = {key: (stock_start[key] + stock_end[key]) / 2.0 for key in CORE_COHORTS}

    current = {
        "FJ": xini["FJ"],
        "FS": xini["FS"],
        "FA": xini["FA"],
        "MJ": xini["MJ"],
        "MS": xini["MS"],
        "MA": xini["MA"],
    }
    offtake = {key: 0.0 for key in TEN_COHORTS}
    final_exact = {key: 0.0 for key in TEN_COHORTS}

    for day in range(1, 367):
        female_birth = current["FA"] * fecundity_female
        male_birth = current["FA"] * fecundity_male

        fec = {
            "FB": female_birth,
            "FJ": current["FJ"],
            "FS": current["FS"],
            "FA": current["FA"],
            "FC": 0.0,
            "MB": male_birth,
            "MJ": current["MJ"],
            "MS": current["MS"],
            "MA": current["MA"],
            "MC": 0.0,
        }
        if day == 366:
            final_exact = dict(fec)
            break

        survived = {}
        for cohort in TEN_COHORTS:
            offtake[cohort] += probability_offtake[cohort] * fec[cohort]
            survived[cohort] = fec[cohort] * (
                1.0 - probability_death[cohort] - probability_offtake[cohort]
            )

        female_cull = probability_growth["FA"] * survived["FA"]
        male_cull = probability_growth["MA"] * survived["MA"]
        offtake["FC"] += female_cull
        offtake["MC"] += male_cull

        current = {
            "FJ": survived["FB"] + (1.0 - probability_growth["FJ"]) * survived["FJ"],
            "FS": probability_growth["FJ"] * survived["FJ"]
            + (1.0 - probability_growth["FS"]) * survived["FS"],
            "FA": probability_growth["FS"] * survived["FS"]
            + (1.0 - probability_growth["FA"]) * survived["FA"],
            "MJ": survived["MB"] + (1.0 - probability_growth["MJ"]) * survived["MJ"],
            "MS": probability_growth["MJ"] * survived["MJ"]
            + (1.0 - probability_growth["MS"]) * survived["MS"],
            "MA": probability_growth["MS"] * survived["MS"]
            + (1.0 - probability_growth["MA"]) * survived["MA"],
        }

    return ProjectedPopulation(
        stock_start,
        stock_end,
        final_exact,
        stock_average,
        offtake,
    )


def calc_summary_offtake(
    cohort_stock_start: dict[str, float],
    cohort_stock_end_projected: dict[str, float],
    cohort_stock_average: dict[str, float],
    cohort_offtake_heads: dict[str, float],
    simulation_duration: float,
) -> dict[str, dict[str, float]]:
    for values, name in (
        (cohort_stock_start, "cohort_stock_start"),
        (cohort_stock_end_projected, "cohort_stock_end_projected"),
        (cohort_stock_average, "cohort_stock_average"),
    ):
        _require_keys(values, CORE_COHORTS, name)
    _require_keys(cohort_offtake_heads, TEN_COHORTS, "cohort_offtake_heads")
    if simulation_duration < 0:
        raise ValueError("simulation_duration must be nonnegative")

    offtake = {
        "FJ": cohort_offtake_heads["FB"] + cohort_offtake_heads["FJ"],
        "FS": cohort_offtake_heads["FS"],
        "FA": cohort_offtake_heads["FA"] + cohort_offtake_heads["FC"],
        "MJ": cohort_offtake_heads["MB"] + cohort_offtake_heads["MJ"],
        "MS": cohort_offtake_heads["MS"],
        "MA": cohort_offtake_heads["MA"] + cohort_offtake_heads["MC"],
    }
    stock_variation = {
        key: cohort_stock_end_projected[key] - cohort_stock_start[key]
        for key in CORE_COHORTS
    }
    combined = {key: stock_variation[key] + offtake[key] for key in CORE_COHORTS}

    def divide(numerator: dict[str, float], denominator: dict[str, float]) -> dict[str, float]:
        return {
            key: numerator[key] / denominator[key] if denominator[key] != 0 else np.nan
            for key in CORE_COHORTS
        }

    return {
        "stock_variation_heads": stock_variation,
        "offtake_heads": offtake,
        "offtake_heads_assessment": {
            key: offtake[key] / 365.0 * simulation_duration for key in CORE_COHORTS
        },
        "offtake_rate_to_stock_start": divide(offtake, cohort_stock_start),
        "offtake_rate_to_stock_average": divide(offtake, cohort_stock_average),
        "offtake_stock_variation_heads": combined,
        "offtake_stock_plus_variation_rate_to_stock_start": divide(
            combined, cohort_stock_start
        ),
        "offtake_stock_plus_variation_rate_to_stock_average": divide(
            combined, cohort_stock_average
        ),
    }
