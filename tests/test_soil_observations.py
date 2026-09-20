from datetime import date

import pytest

from wholefarm.input_schema import SoilLayerObservation, SoilProfile
from wholefarm.soil_observations import (
    quantified_profile_soc_t_c_ha,
    repeated_profile_esm_change_t_c_ha,
    soil_profile_to_layers,
)


def _profile(
    profile_id: str,
    bulk_density: float | None,
    soc: float = 20.0,
) -> SoilProfile:
    return SoilProfile(
        profile_id=profile_id,
        farm_id="farm_1",
        land_unit_id="field_1",
        latitude=0.1,
        longitude=35.1,
        sample_date=date(2026, 1, 1),
        land_use="mixed_crop",
        layers=[
            SoilLayerObservation(
                depth_top_cm=0.0,
                depth_bottom_cm=30.0,
                soc_g_kg=soc,
                bulk_density_g_cm3=bulk_density,
            ),
            SoilLayerObservation(
                depth_top_cm=30.0,
                depth_bottom_cm=45.0,
                soc_g_kg=15.0,
                bulk_density_g_cm3=bulk_density,
            ),
        ],
    )


def test_measured_profile_stock_requires_bulk_density() -> None:
    profile = _profile("p1", None)
    with pytest.raises(ValueError):
        soil_profile_to_layers(profile)


def test_explicit_bulk_density_override_is_supported() -> None:
    profile = _profile("p1", None)
    layers = soil_profile_to_layers(profile, {0: 1.2, 1: 1.3})
    assert layers[0].bulk_density_g_cm3 == 1.2
    assert quantified_profile_soc_t_c_ha(
        profile,
        bulk_density_overrides={0: 1.2, 1: 1.3},
    ) == pytest.approx(72.0)


def test_repeated_profile_esm_change_uses_common_soil_mass() -> None:
    baseline = _profile("baseline", 1.2, soc=20.0)
    intervention = _profile("intervention", 1.0, soc=21.0)
    change = repeated_profile_esm_change_t_c_ha(
        baseline,
        intervention,
        reference_depth_cm=30.0,
    )
    assert change < 0.0
