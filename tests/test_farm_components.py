from datetime import date

from wholefarm.farm_components import run_farm_survey_components
from wholefarm.input_schema import FarmEnergyRecord, FarmSurvey, LandUnit


def test_survey_components_run_without_livestock() -> None:
    survey = FarmSurvey(
        farm_id="farm_1",
        country="Ethiopia",
        basin="Omo Ghibe River Basin",
        survey_date=date(2026, 9, 20),
        land_units=[LandUnit(land_unit_id="field_1", area_ha=1.5, land_use="mixed_crop")],
        energy_records=[
            FarmEnergyRecord(
                source_name="electricity",
                amount=200.0,
                unit="kWh",
                emission_factor_kg_co2e_per_unit=0.4,
            )
        ],
    )
    result = run_farm_survey_components(survey)
    assert result.livestock is None
    assert result.energy.total_known_kg_co2e == 80.0
    assert result.energy.complete
