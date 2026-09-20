"""Farm management aggregation and soil nitrogen source construction."""

from __future__ import annotations

from dataclasses import dataclass

from .input_schema import FarmSurvey, LandUnit
from .soil_ghg import SoilN2OFactors, SoilN2OResult, SoilNitrogenSource, calculate_soil_n2o


@dataclass(frozen=True)
class AnnualLandInputs:
    land_unit_id: str
    year: int
    area_ha: float
    mineral_n_kg: float
    organic_n_kg: float
    plant_c_t: float
    manure_c_t: float


@dataclass(frozen=True)
class NitrogenSourceFactorSet:
    direct_ef_n2on_per_n: float
    volatilized_fraction: float
    leached_fraction: float

    def __post_init__(self) -> None:
        if self.direct_ef_n2on_per_n < 0:
            raise ValueError("direct_ef_n2on_per_n must be nonnegative")
        for value, name in (
            (self.volatilized_fraction, "volatilized_fraction"),
            (self.leached_fraction, "leached_fraction"),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between zero and one")


def aggregate_land_management_year(
    land_unit: LandUnit,
    year: int,
) -> AnnualLandInputs:
    records = [record for record in land_unit.management if record.year == year]
    mineral_n_kg = sum(record.mineral_n_kg_ha for record in records) * land_unit.area_ha
    organic_n_kg = sum(record.organic_n_kg_ha for record in records) * land_unit.area_ha
    plant_c_t = sum(record.plant_c_input_t_ha for record in records) * land_unit.area_ha
    manure_c_t = sum(record.manure_c_input_t_ha for record in records) * land_unit.area_ha
    return AnnualLandInputs(
        land_unit_id=land_unit.land_unit_id,
        year=year,
        area_ha=land_unit.area_ha,
        mineral_n_kg=mineral_n_kg,
        organic_n_kg=organic_n_kg,
        plant_c_t=plant_c_t,
        manure_c_t=manure_c_t,
    )


def aggregate_farm_management_year(
    survey: FarmSurvey,
    year: int,
) -> tuple[AnnualLandInputs, ...]:
    return tuple(
        aggregate_land_management_year(land_unit, year)
        for land_unit in survey.land_units
    )


def calculate_survey_soil_n2o(
    survey: FarmSurvey,
    year: int,
    mineral_factors: NitrogenSourceFactorSet,
    organic_factors: NitrogenSourceFactorSet,
    indirect_factors: SoilN2OFactors,
    gwp_n2o: float = 273.0,
) -> SoilN2OResult:
    annual = aggregate_farm_management_year(survey, year)
    mineral_n = sum(item.mineral_n_kg for item in annual)
    organic_n = sum(item.organic_n_kg for item in annual)

    sources: list[SoilNitrogenSource] = []
    if mineral_n > 0:
        sources.append(
            SoilNitrogenSource(
                name="mineral_fertilizer",
                nitrogen_kg=mineral_n,
                direct_ef_n2on_per_n=mineral_factors.direct_ef_n2on_per_n,
                volatilized_fraction=mineral_factors.volatilized_fraction,
                leached_fraction=mineral_factors.leached_fraction,
            )
        )
    if organic_n > 0:
        sources.append(
            SoilNitrogenSource(
                name="organic_nitrogen",
                nitrogen_kg=organic_n,
                direct_ef_n2on_per_n=organic_factors.direct_ef_n2on_per_n,
                volatilized_fraction=organic_factors.volatilized_fraction,
                leached_fraction=organic_factors.leached_fraction,
            )
        )
    if not sources:
        raise ValueError("No managed nitrogen inputs were recorded for the requested year")

    return calculate_soil_n2o(
        sources,
        indirect_factors,
        gwp_n2o=gwp_n2o,
    )
