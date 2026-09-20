from wholefarm.gleam_core import (
    ManureManagementSystem,
    calc_ch4_enteric,
    calc_ch4_manure,
    calc_conversion_factor_ym,
    calc_milk_production,
    calc_nitrogen_excretion,
    calc_nitrogen_intake,
    calc_nitrogen_retention,
    calc_ration_digestibility,
    calc_volatile_solids,
)


def test_ration_digestibility_matches_reference_case() -> None:
    assert calc_ration_digestibility("CTL", 0.6, 0.7, 0.5) == 0.42


def test_enteric_conversion_factor_reference_values() -> None:
    assert calc_conversion_factor_ym("CTL", "FA", 0.0) == 9.75
    assert calc_conversion_factor_ym("CTL", "FA", 1.0) == 4.75
    assert calc_conversion_factor_ym("PGS", "FJ", 0.65) == 0.0


def test_enteric_ch4_is_positive() -> None:
    ym = calc_conversion_factor_ym("CTL", "FA", 0.6)
    assert calc_ch4_enteric("CTL", ym, 1.0, 18.4, 10.0) > 0


def test_nitrogen_balance_reference_cases() -> None:
    assert calc_nitrogen_intake(10.0, 0.03) == 0.3
    retention = calc_nitrogen_retention(
        "CTL",
        "FA",
        milk_protein_fraction=0.032,
        milk_yield_day=20,
        daily_weight_gain=0.5,
    )
    assert retention > 0
    assert calc_nitrogen_excretion("CTL", 0.5, 0.2) == 0.3


def test_volatile_solids_reference_case() -> None:
    value = calc_volatile_solids(5.0, 0.6, 0.04, 0.08)
    assert value == 5.0 * (1.0 - 0.6 + 0.04) * (1.0 - 0.08)


def test_manure_ch4_reference_case() -> None:
    systems = {
        "mms_burned": ManureManagementSystem(
            0.2,
            methane_conversion_factor_percent=10,
            bo_m3_ch4_per_kg_vs=0.13,
        ),
        "mms_pasture": ManureManagementSystem(
            0.3,
            methane_conversion_factor_percent=0.47,
            bo_m3_ch4_per_kg_vs=0.19,
        ),
        "mms_drylot": ManureManagementSystem(
            0.5,
            methane_conversion_factor_percent=2,
            bo_m3_ch4_per_kg_vs=0.13,
        ),
    }
    result = calc_ch4_manure(2.0, systems)
    expected = 2.0 * 0.67 * 0.3 * 0.0047 * 0.19
    assert abs(result["ch4_manure_pasture"] - expected) < 1e-12


def test_milk_production_reference_case() -> None:
    result = calc_milk_production(
        "CTL",
        "FA",
        10,
        365,
        100,
        0.8,
        0.033,
        0.04,
        0.048,
    )
    assert result.mass_kg == 10 * 365 * 100 * 0.8
    assert abs(result.fpcm_kg - result.mass_kg) < 1e-9
