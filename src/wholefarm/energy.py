"""Farm energy greenhouse gas accounting with explicit emission factor completeness."""

from __future__ import annotations

from dataclasses import dataclass

from .input_schema import FarmEnergyRecord


@dataclass(frozen=True)
class EnergySourceEmission:
    source_name: str
    amount: float
    unit: str
    emission_factor_kg_co2e_per_unit: float | None
    emissions_kg_co2e: float | None


@dataclass(frozen=True)
class EnergyEmissionsResult:
    sources: tuple[EnergySourceEmission, ...]
    total_known_kg_co2e: float
    total_known_t_co2e: float
    complete: bool
    missing_factor_sources: tuple[str, ...]


def calculate_energy_emissions(
    records: list[FarmEnergyRecord],
) -> EnergyEmissionsResult:
    sources: list[EnergySourceEmission] = []
    missing: list[str] = []
    total = 0.0

    for record in records:
        factor = record.emission_factor_kg_co2e_per_unit
        if factor is None:
            emissions = None
            missing.append(record.source_name)
        else:
            emissions = record.amount * factor
            total += emissions
        sources.append(
            EnergySourceEmission(
                source_name=record.source_name,
                amount=record.amount,
                unit=record.unit,
                emission_factor_kg_co2e_per_unit=factor,
                emissions_kg_co2e=emissions,
            )
        )

    return EnergyEmissionsResult(
        sources=tuple(sources),
        total_known_kg_co2e=total,
        total_known_t_co2e=total / 1000.0,
        complete=not missing,
        missing_factor_sources=tuple(missing),
    )
