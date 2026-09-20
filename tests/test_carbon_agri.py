import pytest

from wholefarm.carbon_agri import (
    HedgeEstablishment,
    SequestrationPractice,
    apply_nonpermanence_discount,
    apply_reference_discount,
    carbon_intensity,
    dairy_unit_emission_gain,
    farm_carbon_gain,
    progressive_emission_gain,
    progressive_implementation_multiplier,
    sequestration_gain,
)


def test_carbon_intensity_equation_4() -> None:
    assert carbon_intensity(1000, 500) == 2


def test_progressive_multiplier_for_three_year_implementation_in_five_year_project() -> None:
    assert progressive_implementation_multiplier(3, 5) == 4


def test_meat_or_crop_progressive_gain_equations_6_and_7() -> None:
    gain = progressive_emission_gain(
        initial_intensity_kg_co2e_per_unit=10,
        final_intensity_kg_co2e_per_unit=8,
        average_production_units=100,
        implementation_years=3,
        project_years=5,
    )
    assert gain == 800


def test_dairy_gain_sums_milk_and_meat_equation_5() -> None:
    gain = dairy_unit_emission_gain(
        1.2,
        1.0,
        10000,
        12,
        10,
        500,
        3,
        5,
    )
    assert gain == pytest.approx((0.2 * 10000 + 2 * 500) * 4)


def test_sequestration_equation_8_components() -> None:
    practices = [SequestrationPractice(100, 2, 5, 3)]
    hedge = HedgeEstablishment(2, 100, 4)
    assert sequestration_gain(practices, hedge, 50) == 1750


def test_supplied_methodology_discounts() -> None:
    assert apply_reference_discount(1000, "specific") == 1000
    assert apply_reference_discount(1000, "generic") == 900
    assert apply_nonpermanence_discount(1000, "soil_or_biomass") == 800
    assert apply_nonpermanence_discount(1000, "new_hedge") == 900
    assert apply_nonpermanence_discount(1000, "new_hedge", True) == 1000


def test_farm_carbon_gain_equation_3() -> None:
    result = farm_carbon_gain([100, 200, 300], 400)
    assert result.footprint_gain_kg_co2e == 600
    assert result.farm_carbon_gain_kg_co2e == 1000
