from math import exp

import pytest

from wholefarm.rothc import (
    RothCMonth,
    RothCPools,
    annual_soc_trajectory,
    decompose,
    rmf_plant_cover,
    rmf_temperature,
    step_month,
)


def test_temperature_modifier_matches_reference_formula() -> None:
    assert rmf_temperature(-6.0) == 0.0
    expected = 47.91 / (exp(106.06 / (15.0 + 18.27)) + 1.0)
    assert rmf_temperature(15.0) == pytest.approx(expected)


def test_plant_cover_modifier_matches_reference() -> None:
    assert rmf_plant_cover(0) == 1.0
    assert rmf_plant_cover(1) == 0.6


def test_decomposition_preserves_carbon_balance_before_inputs() -> None:
    pools = RothCPools(1.0, 2.0, 0.5, 10.0, 5.0)
    updated, decomposed, to_co2 = decompose(
        pools,
        clay_percent=30,
        rate_modifier=1.0,
        plant_c_input_t_ha=0.0,
        fym_c_input_t_ha=0.0,
        dpm_rpm_ratio=1.44,
    )
    assert updated.total_soc < pools.total_soc
    assert pools.total_soc - updated.total_soc == pytest.approx(to_co2)
    assert decomposed >= to_co2


def test_month_step_adds_plant_and_manure_carbon() -> None:
    pools = RothCPools(0.0, 0.0, 0.0, 0.0, 5.0)
    month = RothCMonth(
        temperature_c=15,
        rainfall_mm=100,
        open_pan_evaporation_mm=80,
        plant_cover=1,
        plant_c_input_t_ha=1.0,
        fym_c_input_t_ha=1.0,
        dpm_rpm_ratio=1.44,
    )
    result = step_month(pools, month, 30, 30, 0.0)
    assert result.pools.total_soc == pytest.approx(7.0)


def test_annual_trajectory_uses_vm0042_compatible_depth() -> None:
    initial = RothCPools(1.0, 5.0, 1.0, 30.0, 10.0)
    month = RothCMonth(20, 100, 80, 1, 0.5, 0.1, 1.44)
    trajectory = annual_soc_trajectory(initial, [month] * 12, 35, 30)
    assert len(trajectory) == 2
    assert trajectory[0] == initial.total_soc
