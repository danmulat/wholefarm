"""Public CAP2ER Level 2 indicator equations used by the whole farm model.

The public 2022 methodology defines the farm apparent nitrogen balance as
farm nitrogen inputs minus farm nitrogen outputs divided by utilized
agricultural area. Nitrogen efficiency is outputs divided by inputs.
Leaching potential is apparent nitrogen balance minus gaseous nitrogen
losses minus nitrogen storage in soil.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NitrogenIndicators:
    apparent_balance_kg_n_ha: float
    efficiency_fraction: float
    air_losses_kg_n_ha: float
    soil_storage_kg_n_ha: float
    leaching_potential_kg_n_ha: float


def apparent_nitrogen_balance(
    nitrogen_inputs_kg_n: float,
    nitrogen_outputs_kg_n: float,
    utilized_agricultural_area_ha: float,
) -> float:
    if nitrogen_inputs_kg_n < 0 or nitrogen_outputs_kg_n < 0:
        raise ValueError("Nitrogen inputs and outputs must be nonnegative")
    if utilized_agricultural_area_ha <= 0:
        raise ValueError("Utilized agricultural area must be positive")
    return (
        nitrogen_inputs_kg_n - nitrogen_outputs_kg_n
    ) / utilized_agricultural_area_ha


def nitrogen_efficiency(
    nitrogen_inputs_kg_n: float,
    nitrogen_outputs_kg_n: float,
) -> float:
    if nitrogen_inputs_kg_n <= 0:
        raise ValueError("Nitrogen inputs must be positive")
    if nitrogen_outputs_kg_n < 0:
        raise ValueError("Nitrogen outputs must be nonnegative")
    return nitrogen_outputs_kg_n / nitrogen_inputs_kg_n


def soil_nitrogen_storage_from_carbon(
    soil_carbon_storage_kg_c_ha: float,
    carbon_to_nitrogen_ratio: float = 10.0,
) -> float:
    """Convert soil carbon storage to nitrogen storage using a configurable C to N ratio.

    The public CAP2ER methodology states that nitrogen storage is estimated from
    carbon storage using a factor of 10. The model represents that statement as
    a C to N ratio of 10 and keeps the ratio explicit for traceability.
    """

    if carbon_to_nitrogen_ratio <= 0:
        raise ValueError("Carbon to nitrogen ratio must be positive")
    return soil_carbon_storage_kg_c_ha / carbon_to_nitrogen_ratio


def leaching_potential(
    apparent_balance_kg_n_ha: float,
    air_nitrogen_losses_kg_n_ha: float,
    soil_nitrogen_storage_kg_n_ha: float,
) -> float:
    if air_nitrogen_losses_kg_n_ha < 0:
        raise ValueError("Air nitrogen losses must be nonnegative")
    return (
        apparent_balance_kg_n_ha
        - air_nitrogen_losses_kg_n_ha
        - soil_nitrogen_storage_kg_n_ha
    )


def calculate_nitrogen_indicators(
    nitrogen_inputs_kg_n: float,
    nitrogen_outputs_kg_n: float,
    utilized_agricultural_area_ha: float,
    air_nitrogen_losses_kg_n_ha: float,
    soil_carbon_storage_kg_c_ha: float,
    carbon_to_nitrogen_ratio: float = 10.0,
) -> NitrogenIndicators:
    balance = apparent_nitrogen_balance(
        nitrogen_inputs_kg_n,
        nitrogen_outputs_kg_n,
        utilized_agricultural_area_ha,
    )
    efficiency = nitrogen_efficiency(nitrogen_inputs_kg_n, nitrogen_outputs_kg_n)
    soil_storage = soil_nitrogen_storage_from_carbon(
        soil_carbon_storage_kg_c_ha,
        carbon_to_nitrogen_ratio,
    )
    leaching = leaching_potential(
        balance,
        air_nitrogen_losses_kg_n_ha,
        soil_storage,
    )
    return NitrogenIndicators(
        apparent_balance_kg_n_ha=balance,
        efficiency_fraction=efficiency,
        air_losses_kg_n_ha=air_nitrogen_losses_kg_n_ha,
        soil_storage_kg_n_ha=soil_storage,
        leaching_potential_kg_n_ha=leaching,
    )
