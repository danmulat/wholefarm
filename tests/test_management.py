from datetime import date

import pytest

from wholefarm.input_schema import FarmSurvey, LandManagementRecord, LandUnit
from wholefarm.management import (
    NitrogenSourceFactorSet,
    aggregate_farm_management_year,
    calculate_survey_soil_n2o,
)
from wholefarm.soil_ghg import SoilN2OFactors


def _survey() -> FarmSurvey:
    return FarmSurvey(
        farm_id="farm_1",
        country="Kenya",
        basin="Lake Victoria Basin",
        survey_date=date(2026, 9, 20),
        land_units=[
            LandUnit(
                land_unit_id="field_1",
                area_ha=2.0,
                land_use="mixed_crop",
                management=[
                    LandManagementRecord(
                        year=2026,
                        land_use="maize",
                        mineral_n_kg_ha=50.0,
                        organic_n_kg_ha=20.0,
                        plant_c_input_t_ha=2.0,
                        manure_c_input_t_ha=0.5,
                    )
                ],
            ),
            LandUnit(
                land_unit_id="pasture_1",
                area_ha=3.0,
                land_use="pasture",
                management=[
                    LandManagementRecord(
                        year=2026,
                        land_use="pasture",
                        organic_n_kg_ha=10.0,
                        plant_c_input_t_ha=3.0,
                    )
                ],
            ),
        ],
    )


def test_farm_management_aggregation_preserves_area_and_mass() -> None:
    values = aggregate_farm_management_year(_survey(), 2026)
    field = next(item for item in values if item.land_unit_id == "field_1")
    pasture = next(item for item in values if item.land_unit_id == "pasture_1")
    assert field.mineral_n_kg == 100.0
    assert field.organic_n_kg == 40.0
    assert field.plant_c_t == 4.0
    assert pasture.organic_n_kg == 30.0


def test_survey_soil_n2o_uses_explicit_factor_sets() -> None:
    result = calculate_survey_soil_n2o(
        _survey(),
        2026,
        mineral_factors=NitrogenSourceFactorSet(0.01, 0.1, 0.2),
        organic_factors=NitrogenSourceFactorSet(0.01, 0.2, 0.1),
        indirect_factors=SoilN2OFactors(0.01, 0.011),
    )
    assert result.nitrogen_applied_kg == pytest.approx(170.0)
    assert result.total_n2o_kg > 0
