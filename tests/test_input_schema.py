from datetime import date

import pytest
from pydantic import ValidationError

from wholefarm.input_schema import (
    FarmSurvey,
    LandUnit,
    SoilLayerObservation,
    SoilProfile,
)


def _profile(depth_bottom: float, purpose: str = "quantification") -> SoilProfile:
    return SoilProfile(
        profile_id="p1",
        farm_id="f1",
        land_unit_id="field1",
        latitude=0.1,
        longitude=35.1,
        sample_date=date(2026, 1, 1),
        land_use="mixed_crop",
        purpose=purpose,
        extrapolation_method=(
            "locally validated depth function" if purpose == "calibration_validation" else None
        ),
        layers=[
            SoilLayerObservation(
                depth_top_cm=0.0,
                depth_bottom_cm=depth_bottom,
                soc_g_kg=20.0,
                bulk_density_g_cm3=1.2,
            )
        ],
    )


def test_quantification_profile_requires_vm0042_depth() -> None:
    with pytest.raises(ValidationError):
        _profile(20.0)


def test_shallow_legacy_profile_can_be_calibration_data() -> None:
    profile = _profile(20.0, "calibration_validation")
    assert profile.sampled_depth_cm == 20.0


def test_farm_survey_links_profiles_to_land_units() -> None:
    survey = FarmSurvey(
        farm_id="f1",
        country="Kenya",
        basin="Lake Victoria Basin",
        survey_date=date(2026, 1, 1),
        land_units=[LandUnit(land_unit_id="field1", area_ha=2.0, land_use="mixed_crop")],
        soil_profiles=[_profile(30.0)],
    )
    assert survey.total_area_ha == 2.0


def test_soil_profile_rejects_layer_gap() -> None:
    with pytest.raises(ValidationError):
        SoilProfile(
            profile_id="p2",
            farm_id="f1",
            land_unit_id="field1",
            latitude=0.1,
            longitude=35.1,
            sample_date=date(2026, 1, 1),
            land_use="pasture",
            layers=[
                SoilLayerObservation(
                    depth_top_cm=0.0,
                    depth_bottom_cm=10.0,
                    soc_g_kg=20.0,
                    bulk_density_g_cm3=1.2,
                ),
                SoilLayerObservation(
                    depth_top_cm=15.0,
                    depth_bottom_cm=30.0,
                    soc_g_kg=15.0,
                    bulk_density_g_cm3=1.3,
                ),
            ],
        )
