"""Run validated farm survey components that do not require SOC scenario assumptions."""

from __future__ import annotations

from dataclasses import dataclass

from .energy import EnergyEmissionsResult, calculate_energy_emissions
from .input_adapters import farm_survey_to_livestock_specs
from .input_schema import FarmSurvey
from .livestock_farm import LivestockFarmResult, run_livestock_farm


@dataclass(frozen=True)
class FarmSurveyComponents:
    farm_id: str
    livestock: LivestockFarmResult | None
    energy: EnergyEmissionsResult


def run_farm_survey_components(
    survey: FarmSurvey,
    gwp_ch4: float = 27.2,
    gwp_n2o: float = 273.0,
) -> FarmSurveyComponents:
    specs = farm_survey_to_livestock_specs(survey)
    livestock = (
        run_livestock_farm(specs, gwp_ch4=gwp_ch4, gwp_n2o=gwp_n2o)
        if specs
        else None
    )
    energy = calculate_energy_emissions(survey.energy_records)
    return FarmSurveyComponents(
        farm_id=survey.farm_id,
        livestock=livestock,
        energy=energy,
    )
