from wholefarm.energy import calculate_energy_emissions
from wholefarm.input_schema import FarmEnergyRecord


def test_energy_emissions_sum_explicit_factors() -> None:
    result = calculate_energy_emissions(
        [
            FarmEnergyRecord(
                source_name="electricity",
                amount=1000.0,
                unit="kWh",
                emission_factor_kg_co2e_per_unit=0.5,
            ),
            FarmEnergyRecord(
                source_name="diesel",
                amount=100.0,
                unit="litre",
                emission_factor_kg_co2e_per_unit=2.7,
            ),
        ]
    )
    assert result.total_known_kg_co2e == 770.0
    assert result.total_known_t_co2e == 0.77
    assert result.complete


def test_missing_energy_factor_is_flagged_not_zeroed_as_complete() -> None:
    result = calculate_energy_emissions(
        [
            FarmEnergyRecord(
                source_name="electricity",
                amount=1000.0,
                unit="kWh",
            )
        ]
    )
    assert result.total_known_kg_co2e == 0.0
    assert not result.complete
    assert result.missing_factor_sources == ("electricity",)
    assert result.sources[0].emissions_kg_co2e is None
