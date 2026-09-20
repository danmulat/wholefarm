import pytest

from wholefarm.nutrient_flow import ManureRecoveryConfig, route_manure_to_fields


def test_manure_recovery_mass_flow() -> None:
    config = ManureRecoveryConfig(
        collection_fraction=0.8,
        storage_n_retention_fraction=0.75,
        field_application_fraction=0.9,
        volatile_solids_recovery_fraction=0.7,
        carbon_fraction_of_recovered_vs=0.5,
    )
    result = route_manure_to_fields(100.0, 1000.0, config)
    assert result.collected_n_kg == pytest.approx(80.0)
    assert result.retained_after_storage_n_kg == pytest.approx(60.0)
    assert result.field_applied_n_kg == pytest.approx(54.0)
    assert result.recovered_vs_kg == pytest.approx(560.0)
    assert result.field_applied_c_kg == pytest.approx(252.0)
    assert result.field_applied_c_t_ha(2.0) == pytest.approx(0.126)
    assert result.field_applied_n_kg_ha(2.0) == pytest.approx(27.0)


def test_manure_recovery_requires_explicit_valid_fractions() -> None:
    with pytest.raises(ValueError):
        ManureRecoveryConfig(
            collection_fraction=1.2,
            storage_n_retention_fraction=0.75,
            field_application_fraction=0.9,
            volatile_solids_recovery_fraction=0.7,
            carbon_fraction_of_recovered_vs=0.5,
        )
