"""CARBON AGRI project accounting equations from the supplied 2019 methodology.

This module keeps CARBON AGRI accounting separate from the scientific process
models. It accepts emissions and removals calculated elsewhere and applies the
project duration, progressive implementation, unit intensity, and discount rules
defined in the supplied methodology.
"""

from __future__ import annotations

from dataclasses import dataclass

MAX_PROJECT_YEARS = 5


@dataclass(frozen=True)
class UnitEmissionGain:
    unit_name: str
    initial_intensity_kg_co2e_per_unit: float
    final_intensity_kg_co2e_per_unit: float
    average_production_units: float
    implementation_years: int
    project_years: int

    @property
    def intensity_reduction(self) -> float:
        return (
            self.initial_intensity_kg_co2e_per_unit
            - self.final_intensity_kg_co2e_per_unit
        )

    @property
    def project_gain_kg_co2e(self) -> float:
        return progressive_emission_gain(
            self.initial_intensity_kg_co2e_per_unit,
            self.final_intensity_kg_co2e_per_unit,
            self.average_production_units,
            self.implementation_years,
            self.project_years,
        )


@dataclass(frozen=True)
class SequestrationPractice:
    annual_factor_kg_co2e_ha_year: float
    initial_area_ha: float
    final_area_ha: float
    duration_years: float

    @property
    def gain_kg_co2e(self) -> float:
        return (
            self.annual_factor_kg_co2e_ha_year
            * (self.final_area_ha - self.initial_area_ha)
            * self.duration_years
        )


@dataclass(frozen=True)
class HedgeEstablishment:
    annual_factor_kg_co2e_m_year: float
    established_length_m: float
    duration_years: float

    @property
    def gain_kg_co2e(self) -> float:
        return (
            self.annual_factor_kg_co2e_m_year
            * self.established_length_m
            * self.duration_years
        )


@dataclass(frozen=True)
class CarbonAgriGain:
    footprint_gain_kg_co2e: float
    sequestration_gain_kg_co2e: float

    @property
    def farm_carbon_gain_kg_co2e(self) -> float:
        return self.footprint_gain_kg_co2e + self.sequestration_gain_kg_co2e


def validate_project_timing(implementation_years: int, project_years: int) -> None:
    if not 1 <= project_years <= MAX_PROJECT_YEARS:
        raise ValueError("CARBON AGRI project duration must be between one and five years")
    if not 1 <= implementation_years <= project_years:
        raise ValueError("Implementation years must be between one and project duration")


def carbon_intensity(
    total_unit_emissions_kg_co2e: float,
    total_unit_output: float,
) -> float:
    if total_unit_output <= 0:
        raise ValueError("Total unit output must be positive")
    return total_unit_emissions_kg_co2e / total_unit_output


def progressive_implementation_multiplier(
    implementation_years: int,
    project_years: int,
) -> float:
    """Return the cumulative multiplier used in CARBON AGRI Equations 5 to 7."""

    validate_project_timing(implementation_years, project_years)
    implementation_sum = implementation_years * (implementation_years + 1) / 2
    return implementation_sum / implementation_years + (
        project_years - implementation_years
    )


def progressive_emission_gain(
    initial_intensity_kg_co2e_per_unit: float,
    final_intensity_kg_co2e_per_unit: float,
    average_production_units: float,
    implementation_years: int,
    project_years: int,
) -> float:
    if average_production_units < 0:
        raise ValueError("Average production must be nonnegative")
    multiplier = progressive_implementation_multiplier(
        implementation_years,
        project_years,
    )
    intensity_difference = (
        initial_intensity_kg_co2e_per_unit
        - final_intensity_kg_co2e_per_unit
    )
    return intensity_difference * average_production_units * multiplier


def dairy_unit_emission_gain(
    milk_initial_intensity: float,
    milk_final_intensity: float,
    average_corrected_milk_kg: float,
    dairy_meat_initial_intensity: float,
    dairy_meat_final_intensity: float,
    average_adjusted_live_weight_kg: float,
    implementation_years: int,
    project_years: int,
) -> float:
    milk_gain = progressive_emission_gain(
        milk_initial_intensity,
        milk_final_intensity,
        average_corrected_milk_kg,
        implementation_years,
        project_years,
    )
    meat_gain = progressive_emission_gain(
        dairy_meat_initial_intensity,
        dairy_meat_final_intensity,
        average_adjusted_live_weight_kg,
        implementation_years,
        project_years,
    )
    return milk_gain + meat_gain


def sequestration_gain(
    practices: list[SequestrationPractice],
    hedge: HedgeEstablishment | None = None,
    indirect_n2o_effect_kg_co2e: float = 0.0,
) -> float:
    total = sum(item.gain_kg_co2e for item in practices)
    if hedge is not None:
        total += hedge.gain_kg_co2e
    return total + indirect_n2o_effect_kg_co2e


def apply_reference_discount(
    value_kg_co2e: float,
    reference: str,
) -> float:
    discount = 0.0 if reference == "specific" else 0.10
    return value_kg_co2e * (1.0 - discount)


def apply_energy_certificate_discount(
    eligible_energy_gain_kg_co2e: float,
    certificate_contracted_during_project: bool,
) -> float:
    if not certificate_contracted_during_project:
        return eligible_energy_gain_kg_co2e
    return eligible_energy_gain_kg_co2e * 0.80


def apply_nonpermanence_discount(
    sequestration_gain_kg_co2e: float,
    source: str,
    sustainable_hedge_management_plan: bool = False,
) -> float:
    if source == "soil_or_biomass":
        return sequestration_gain_kg_co2e * 0.80
    if sustainable_hedge_management_plan:
        return sequestration_gain_kg_co2e
    return sequestration_gain_kg_co2e * 0.90


def farm_carbon_gain(
    unit_footprint_gains_kg_co2e: list[float],
    sequestration_gain_kg_co2e: float,
) -> CarbonAgriGain:
    footprint = float(sum(unit_footprint_gains_kg_co2e))
    return CarbonAgriGain(
        footprint_gain_kg_co2e=footprint,
        sequestration_gain_kg_co2e=sequestration_gain_kg_co2e,
    )
