import pytest

from wholefarm.soc_stock import (
    SoilLayer,
    equivalent_soil_mass_change_t_c_ha,
    equivalent_soil_mass_soc_t_c_ha,
    fine_soil_mass_t_ha,
    reference_soil_mass_t_ha,
)


def test_fine_soil_mass_unit_conversion() -> None:
    mass = fine_soil_mass_t_ha(
        bulk_density_g_cm3=1.2,
        depth_top_cm=0.0,
        depth_bottom_cm=10.0,
        coarse_fragment_percent=0.0,
    )
    assert mass == pytest.approx(1200.0)


def test_reference_soil_mass_to_thirty_cm() -> None:
    layers = [
        SoilLayer(20.0, 1.2, 0.0, 10.0),
        SoilLayer(15.0, 1.3, 10.0, 30.0),
    ]
    assert reference_soil_mass_t_ha(layers, 30.0) == pytest.approx(
        1200.0 + 2600.0
    )


def test_equivalent_soil_mass_uses_fraction_of_last_layer() -> None:
    layers = [
        SoilLayer(20.0, 1.0, 0.0, 10.0),
        SoilLayer(10.0, 1.0, 10.0, 30.0),
    ]
    stock = equivalent_soil_mass_soc_t_c_ha(layers, 1500.0)
    expected = 1000.0 * 20.0 / 1000.0 + 500.0 * 10.0 / 1000.0
    assert stock == pytest.approx(expected)


def test_equivalent_soil_mass_change_removes_bulk_density_mass_artifact() -> None:
    baseline = [
        SoilLayer(20.0, 1.2, 0.0, 30.0),
        SoilLayer(15.0, 1.2, 30.0, 40.0),
    ]
    intervention = [
        SoilLayer(20.0, 1.0, 0.0, 30.0),
        SoilLayer(15.0, 1.0, 30.0, 45.0),
    ]
    change = equivalent_soil_mass_change_t_c_ha(
        baseline,
        intervention,
        reference_depth_cm=30.0,
    )
    reference_mass = 1.2 * 30.0 * 100.0
    expected_baseline = reference_mass * 20.0 / 1000.0
    expected_intervention = (
        1.0 * 30.0 * 100.0 * 20.0 / 1000.0
        + 600.0 * 15.0 / 1000.0
    )
    assert change == pytest.approx(expected_intervention - expected_baseline)


def test_equivalent_soil_mass_requires_enough_profile_mass() -> None:
    layers = [SoilLayer(20.0, 1.0, 0.0, 10.0)]
    with pytest.raises(ValueError):
        equivalent_soil_mass_soc_t_c_ha(layers, 2000.0)
