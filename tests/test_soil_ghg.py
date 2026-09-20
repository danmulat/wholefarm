import pytest

from wholefarm.soil_ghg import (
    SoilN2OFactors,
    SoilNitrogenSource,
    calculate_soil_n2o,
)


def test_source_explicit_soil_n2o_mass_balance() -> None:
    sources = [
        SoilNitrogenSource(
            name="mineral_fertilizer",
            nitrogen_kg=100.0,
            direct_ef_n2on_per_n=0.01,
            volatilized_fraction=0.1,
            leached_fraction=0.2,
        ),
        SoilNitrogenSource(
            name="recovered_manure",
            nitrogen_kg=50.0,
            direct_ef_n2on_per_n=0.01,
            volatilized_fraction=0.2,
            leached_fraction=0.1,
        ),
    ]
    factors = SoilN2OFactors(
        ef4_n2on_per_volatilized_n=0.01,
        ef5_n2on_per_leached_n=0.011,
    )
    result = calculate_soil_n2o(sources, factors)

    expected_direct = (100.0 * 0.01 + 50.0 * 0.01) * 44.0 / 28.0
    expected_vol = (100.0 * 0.1 + 50.0 * 0.2) * 0.01 * 44.0 / 28.0
    expected_leach = (100.0 * 0.2 + 50.0 * 0.1) * 0.011 * 44.0 / 28.0

    assert result.direct_n2o_kg == pytest.approx(expected_direct)
    assert result.volatilization_n2o_kg == pytest.approx(expected_vol)
    assert result.leaching_n2o_kg == pytest.approx(expected_leach)
    assert result.total_n2o_kg == pytest.approx(
        expected_direct + expected_vol + expected_leach
    )
    assert result.nitrogen_applied_kg == pytest.approx(150.0)


def test_soil_n2o_requires_explicit_sources() -> None:
    factors = SoilN2OFactors(0.01, 0.011)
    with pytest.raises(ValueError):
        calculate_soil_n2o([], factors)
