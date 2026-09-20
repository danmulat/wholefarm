"""GLEAM cohort aggregation and gas conversion from the pinned FAO source.

This module preserves the GLEAM gas conversion sets independently from the
whole farm reporting layer. In the pinned GLEAM source, AR6 uses CH4 equal to
27 and N2O equal to 273. CAP2ER reporting may use a different methane value,
so the two conversion contexts must not be silently mixed.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

GWP_SETS = {
    "AR6": {"CH4": 27.0, "N2O": 273.0, "CO2": 1.0},
    "AR5_excluding_carbon_feedback": {"CH4": 28.0, "N2O": 265.0, "CO2": 1.0},
    "AR5_including_carbon_feedback": {"CH4": 34.0, "N2O": 298.0, "CO2": 1.0},
    "AR4": {"CH4": 25.0, "N2O": 298.0, "CO2": 1.0},
}


def _feed_emission_sources(feed_emissions_list: Sequence[object]) -> set[str]:
    sources: set[str] = set()
    for item in feed_emissions_list:
        if isinstance(item, str):
            sources.add(item)
        elif isinstance(item, dict) and "emissions_source" in item:
            sources.add(str(item["emissions_source"]))
        else:
            source = getattr(item, "emissions_source", None)
            if source is None:
                raise ValueError("Feed emission entries require emissions_source")
            sources.add(str(source))
    return sources


def calc_cohort_totals(
    value: float,
    cohort_stock_size: float,
    ration_intake: float,
    feed_emissions_list: Sequence[object],
    simulation_duration: float,
    variable_name: str,
    variable_type: str,
) -> float:
    """Scale one GLEAM variable to cohort total for the assessment duration."""

    if value < 0:
        raise ValueError("value must be nonnegative")
    if cohort_stock_size < 0:
        raise ValueError("cohort_stock_size must be nonnegative")
    if ration_intake < 0:
        raise ValueError("ration_intake must be nonnegative")
    if simulation_duration <= 0:
        raise ValueError("simulation_duration must be positive")
    if variable_type not in {"Production", "Emissions", "Feed", "NitrogenBalance"}:
        raise ValueError("variable_type is not supported")

    feed_sources = _feed_emission_sources(feed_emissions_list)
    if variable_type == "Production":
        return float(value)
    if variable_type == "Emissions" and variable_name in feed_sources:
        return float(
            value
            * ration_intake
            * cohort_stock_size
            * simulation_duration
            / 1000.0
        )
    return float(value * cohort_stock_size * simulation_duration)


def calc_allocated_emissions(
    value: float | Sequence[float],
    allocation_share: float | Sequence[float],
) -> float | np.ndarray:
    """Apply allocation shares with scalar or vector inputs."""

    values = np.asarray(value, dtype=float)
    shares = np.asarray(allocation_share, dtype=float)
    if values.shape != shares.shape and values.ndim > 0 and shares.ndim > 0:
        raise ValueError("value and allocation_share must have the same length")
    if np.any(values < 0):
        raise ValueError("value must be nonnegative")
    if np.any((shares < 0) | (shares > 1)):
        raise ValueError("allocation_share must be between zero and one")
    result = values * shares
    if result.ndim == 0:
        return float(result)
    return result


def calc_co2eq(
    gas: str | Sequence[str],
    value_allocated: float | Sequence[float],
    global_warming_potential_set: str,
) -> dict[str, float | np.ndarray]:
    """Convert allocated CH4, N2O and CO2 to CO2 equivalent using GLEAM GWP sets."""

    if global_warming_potential_set not in GWP_SETS:
        raise ValueError(
            f"global_warming_potential_set must be one of {tuple(GWP_SETS)}"
        )
    gases = np.asarray(gas, dtype=object)
    values = np.asarray(value_allocated, dtype=float)
    if gases.shape != values.shape and gases.ndim > 0 and values.ndim > 0:
        raise ValueError("gas and value_allocated must have the same length")
    if np.any(values < 0):
        raise ValueError("value_allocated must be nonnegative")

    factors = GWP_SETS[global_warming_potential_set]
    flat_gases = gases.reshape(-1)
    invalid = sorted({str(item) for item in flat_gases if str(item) not in factors})
    if invalid:
        raise ValueError(f"gas must be one of {tuple(factors)}")

    gwp = np.asarray([factors[str(item)] for item in flat_gases], dtype=float).reshape(
        gases.shape
    )
    co2eq = values * gwp
    if co2eq.ndim == 0:
        return {"value_co2eq": float(co2eq), "gwp": float(gwp)}
    return {"value_co2eq": co2eq, "gwp": gwp}