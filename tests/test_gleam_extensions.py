import pytest

from wholefarm.gleam_core import (
    calc_fibre_production,
    calc_n2o_manure_total,
    calc_ration_metabolizable_energy,
    calc_ration_urinary_energy_fraction,
)


def test_ration_metabolizable_energy_reference_cases() -> None:
    assert calc_ration_metabolizable_energy("CTL", 0.6, 10, 12) == 6
    assert calc_ration_metabolizable_energy("PGS", 0.6, 10, 12) == pytest.approx(7.2)


def test_ration_urinary_energy_reference_cases() -> None:
    assert calc_ration_urinary_energy_fraction("CTL", 0.6, 0.12, 0.02) == 0.072
    assert calc_ration_urinary_energy_fraction("PGS", 0.6, 0.12, 0.02) == 0.012


def test_fibre_production_reference_case() -> None:
    assert calc_fibre_production("SHP", "FA", 5, 365, 10) == 50
    assert calc_fibre_production("CTL", "FA", 5, 365, 10) == 0


def test_n2o_total_reference_case() -> None:
    result = calc_n2o_manure_total(
        0.0129,
        0.0012,
        0,
        0,
        0.052,
        0.00027,
        0.009,
        0,
        0.01033,
    )
    assert result["n2o_manure_pasture_indirect"] == 0.0129 + 0.0012
    assert result["n2o_manure_other_total"] == 0.052 + 0.00027 + 0.01033
