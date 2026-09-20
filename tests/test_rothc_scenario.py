import pytest

from wholefarm.rothc import RothCPools
from wholefarm.rothc_scenario import (
    MonthlyClimate,
    build_rothc_year,
    distribute_annual_carbon,
    repeat_rothc_year,
    run_rothc_baseline_intervention,
    run_rothc_scenario,
)


def _climate() -> tuple[MonthlyClimate, ...]:
    return tuple(
        MonthlyClimate(
            temperature_c=20.0,
            rainfall_mm=80.0,
            open_pan_evaporation_mm=90.0,
            plant_cover=1,
        )
        for _ in range(12)
    )


def test_distribute_annual_carbon_preserves_total() -> None:
    monthly = distribute_annual_carbon(2.4, [1.0 / 12.0] * 12)
    assert sum(monthly) == pytest.approx(2.4)


def test_rothc_scenario_enforces_vm0042_depth() -> None:
    initial = RothCPools(1.0, 4.0, 1.0, 20.0, 4.0)
    year = build_rothc_year(
        _climate(),
        distribute_annual_carbon(4.0, [1.0 / 12.0] * 12),
        distribute_annual_carbon(1.0, [1.0 / 12.0] * 12),
        dpm_rpm_ratio=1.44,
    )
    with pytest.raises(ValueError):
        run_rothc_scenario(initial, year, clay_percent=30.0, depth_cm=20.0, area_ha=1.0)


def test_intervention_manure_carbon_changes_rothc_result() -> None:
    initial = RothCPools(1.0, 4.0, 1.0, 20.0, 4.0)
    plant = distribute_annual_carbon(4.0, [1.0 / 12.0] * 12)
    baseline_manure = distribute_annual_carbon(0.5, [1.0 / 12.0] * 12)
    intervention_manure = distribute_annual_carbon(2.0, [1.0 / 12.0] * 12)

    baseline_year = build_rothc_year(_climate(), plant, baseline_manure, 1.44)
    intervention_year = build_rothc_year(_climate(), plant, intervention_manure, 1.44)

    baseline, intervention = run_rothc_baseline_intervention(
        initial,
        repeat_rothc_year(baseline_year, 3),
        repeat_rothc_year(intervention_year, 3),
        clay_percent=30.0,
        depth_cm=30.0,
        area_ha=2.0,
    )
    assert intervention.final_soc_t_c_ha > baseline.final_soc_t_c_ha
    assert intervention.stock_change_co2e_t > baseline.stock_change_co2e_t
