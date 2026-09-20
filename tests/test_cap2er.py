import pytest

from wholefarm.cap2er import (
    apparent_nitrogen_balance,
    calculate_nitrogen_indicators,
    nitrogen_efficiency,
    soil_nitrogen_storage_from_carbon,
)


def test_cap2er_apparent_nitrogen_balance() -> None:
    assert apparent_nitrogen_balance(1200, 800, 20) == 20


def test_cap2er_nitrogen_efficiency() -> None:
    assert nitrogen_efficiency(1200, 800) == pytest.approx(2 / 3)


def test_cap2er_soil_n_storage_uses_explicit_ratio() -> None:
    assert soil_nitrogen_storage_from_carbon(100, 10) == 10


def test_cap2er_combined_nitrogen_indicators() -> None:
    result = calculate_nitrogen_indicators(
        nitrogen_inputs_kg_n=1200,
        nitrogen_outputs_kg_n=800,
        utilized_agricultural_area_ha=20,
        air_nitrogen_losses_kg_n_ha=4,
        soil_carbon_storage_kg_c_ha=50,
    )
    assert result.apparent_balance_kg_n_ha == 20
    assert result.soil_storage_kg_n_ha == 5
    assert result.leaching_potential_kg_n_ha == 11
