"""Numerical parity cases copied from the pinned FAO GLEAM test suite.

Reference:
un-fao/GLEAM
commit 90e416197e89093c4f3a347b263ba805d33d4aac

These tests intentionally use the same simple numeric examples as the upstream
R tests so equation drift is visible during Python development.
"""

import math

import pytest

from wholefarm.gleam_core import (
    ManureManagementSystem,
    calc_ch4_manure,
    calc_conversion_factor_ym,
    calc_feed_digestibility_fraction,
    calc_n2o_manure_direct,
    calc_n2o_manure_volatilization,
    calc_nitrogen_excretion,
    calc_nitrogen_intake,
    calc_nitrogen_retention,
    calc_ration_ash,
    calc_ration_digestibility,
    calc_ration_gross_energy,
    calc_ration_metabolizable_energy,
    calc_ration_nitrogen_content,
    calc_ration_urinary_energy_fraction,
    calc_volatile_solids,
)
from wholefarm.gleam_energy import (
    calc_metabolic_energy_req_fibre,
    calc_metabolic_energy_req_pregnancy,
    calc_metabolic_energy_req_work,
    calc_ration_intake,
    calc_reg_growth,
    calc_rem_maintenance,
    calc_total_metabolic_energy_req,
)
from wholefarm.gleam_weights import (
    calc_avg_weights,
    calc_cohort_weights,
    calc_daily_weight_gain,
)


def test_pinned_ration_quality_reference_cases() -> None:
    digestibility = calc_feed_digestibility_fraction(8.0, 7.0, 16.0)
    assert digestibility["feed_digestibility_fraction_ruminant"] == pytest.approx(0.5)
    assert digestibility["feed_digestibility_fraction_pigs"] == pytest.approx(0.4375)

    missing_ruminant = calc_feed_digestibility_fraction(float("nan"), 7.0, 16.0)
    assert missing_ruminant["feed_digestibility_fraction_ruminant"] == 0.0

    assert calc_ration_digestibility("CTL", 0.6, 0.7, 0.5) == pytest.approx(0.42)
    assert calc_ration_digestibility("PGS", 0.6, 0.7, 0.5) == pytest.approx(0.3)
    assert calc_ration_metabolizable_energy("CTL", 0.6, 10.0, 12.0) == pytest.approx(6.0)
    assert calc_ration_metabolizable_energy("PGS", 0.6, 10.0, 12.0) == pytest.approx(7.2)
    assert calc_ration_gross_energy(0.6, 18.0) == pytest.approx(10.8)
    assert calc_ration_nitrogen_content(0.6, 0.02) == pytest.approx(0.012)
    assert calc_ration_urinary_energy_fraction("CTL", 0.6, 0.12, 0.02) == pytest.approx(0.072)
    assert calc_ration_urinary_energy_fraction("PGS", 0.6, 0.12, 0.02) == pytest.approx(0.012)
    assert calc_ration_ash(0.6, 10.0) == pytest.approx(0.06)


def test_pinned_enteric_reference_cases() -> None:
    assert calc_conversion_factor_ym("CTL", "FA", 0.0) == pytest.approx(9.75)
    assert calc_conversion_factor_ym("CTL", "FA", 1.0) == pytest.approx(4.75)
    assert calc_conversion_factor_ym("PGS", "FA", 0.65) == pytest.approx(1.01)
    assert calc_conversion_factor_ym("PGS", "FJ", 0.65) == 0.0
    assert calc_conversion_factor_ym("BFL", "FA", 0.6) == pytest.approx(
        calc_conversion_factor_ym("CTL", "FA", 0.6)
    )


def test_pinned_nitrogen_reference_cases() -> None:
    assert calc_nitrogen_intake(10.0, 0.03) == pytest.approx(0.3)
    assert calc_nitrogen_intake(2.5, 0.04) == pytest.approx(0.1)

    cattle_base = calc_nitrogen_retention(
        "CTL",
        "FA",
        milk_protein_fraction=0.032,
        milk_yield_day=20.0,
        daily_weight_gain=0.0,
        fibre_yield_year=0.0,
        litter_size=1.0,
        parturition_rate=1.0,
    )
    cattle_growth = calc_nitrogen_retention(
        "CTL",
        "FA",
        milk_protein_fraction=0.032,
        milk_yield_day=20.0,
        daily_weight_gain=0.5,
        fibre_yield_year=0.0,
        litter_size=1.0,
        parturition_rate=1.0,
    )
    assert cattle_growth - cattle_base == pytest.approx(0.5 * 0.0326, abs=1e-12)

    goat_base = calc_nitrogen_retention(
        "GTS",
        "FA",
        daily_weight_gain=0.0,
        fibre_yield_year=0.0,
        litter_size=1.0,
        parturition_rate=1.0,
    )
    goat_fibre = calc_nitrogen_retention(
        "GTS",
        "FA",
        daily_weight_gain=0.0,
        fibre_yield_year=10.0,
        litter_size=1.0,
        parturition_rate=1.0,
    )
    assert goat_fibre - goat_base == pytest.approx((10.0 / 365.0) * 0.134, abs=1e-12)

    pig_fa = calc_nitrogen_retention(
        "PGS",
        "FA",
        litter_size=10.0,
        parturition_rate=2.0,
        live_weight_at_weaning=30.0,
        live_weight_at_birth=1.0,
    )
    expected_pig_fa = (
        (0.025 * 10.0 * 2.0 * (30.0 - 1.0) / 0.98)
        + (0.025 * 10.0 * 2.0 * 1.0)
    ) / 365.0
    assert pig_fa == pytest.approx(expected_pig_fa, abs=1e-12)

    pig_fs = calc_nitrogen_retention(
        "PGS",
        "FS",
        daily_weight_gain=0.5,
        litter_size=12.0,
        parturition_rate=2.2,
        live_weight_at_weaning=20.0,
        live_weight_at_birth=1.0,
        pregnancy_duration=115.0,
        cohort_duration_days=200.0,
    )
    expected_pig_fs = 0.025 * 0.5 + (
        0.025 * 12.0 * (115.0 / 200.0) * 1.0 / 0.806
    ) / 365.0
    assert pig_fs == pytest.approx(expected_pig_fs, abs=1e-12)
    assert calc_nitrogen_excretion("CTL", 0.5, 0.2) == pytest.approx(0.3)


def _mms() -> dict[str, ManureManagementSystem]:
    return {
        "mms_burned": ManureManagementSystem(
            fraction=0.2,
            methane_conversion_factor_percent=10.0,
            bo_m3_ch4_per_kg_vs=0.13,
            n2o_ef3=0.0,
            n2o_ef4=0.14,
            nitrogen_fracgas=0.0,
        ),
        "mms_pasture": ManureManagementSystem(
            fraction=0.3,
            methane_conversion_factor_percent=0.47,
            bo_m3_ch4_per_kg_vs=0.19,
            n2o_ef3=0.02,
            n2o_ef4=0.14,
            nitrogen_fracgas=0.21,
        ),
        "mms_drylot": ManureManagementSystem(
            fraction=0.5,
            methane_conversion_factor_percent=2.0,
            bo_m3_ch4_per_kg_vs=0.13,
            n2o_ef3=0.01,
            n2o_ef4=0.14,
            nitrogen_fracgas=0.3,
        ),
    }


def test_pinned_manure_reference_cases() -> None:
    vs = calc_volatile_solids(5.0, 0.6, 0.04, 0.08)
    assert vs == pytest.approx(5.0 * (1.0 - 0.6 + 0.04) * (1.0 - 0.08))

    methane = calc_ch4_manure(2.0, _mms(), methane_density_kg_m3=0.67)
    assert methane["ch4_manure_pasture"] == pytest.approx(
        2.0 * 0.67 * 0.3 * (0.47 / 100.0) * 0.19
    )
    assert methane["ch4_manure_burned"] == pytest.approx(
        2.0 * 0.67 * 0.2 * (10.0 / 100.0) * 0.13
    )
    assert methane["ch4_manure_other"] == pytest.approx(
        2.0 * 0.67 * 0.5 * (2.0 / 100.0) * 0.13
    )

    direct = calc_n2o_manure_direct(0.9, _mms())
    assert direct["n2o_manure_pasture_direct"] == pytest.approx(
        0.9 * (44.0 / 28.0) * 0.3 * 0.02
    )
    assert direct["n2o_manure_other_direct"] == pytest.approx(
        0.9 * (44.0 / 28.0) * 0.5 * 0.01
    )

    volatilization = calc_n2o_manure_volatilization(0.9, _mms())
    assert volatilization["n2o_manure_pasture_vol"] == pytest.approx(
        0.9 * (44.0 / 28.0) * 0.3 * 0.21 * 0.14
    )
    assert volatilization["n2o_manure_other_vol"] == pytest.approx(
        0.9 * (44.0 / 28.0) * 0.5 * 0.3 * 0.14
    )


def test_pinned_weight_reference_cases() -> None:
    juvenile = calc_cohort_weights(
        "FJ",
        500.0,
        600.0,
        35.0,
        480.0,
        550.0,
        90.0,
    )
    assert juvenile.live_weight_cohort_initial == pytest.approx(35.0)
    assert juvenile.live_weight_cohort_potential_final == pytest.approx(90.0)
    assert juvenile.live_weight_cohort_at_slaughter == pytest.approx(90.0)

    adult = calc_cohort_weights(
        "FA",
        70.0,
        90.0,
        4.0,
        65.0,
        85.0,
        18.0,
    )
    assert adult.live_weight_cohort_initial == pytest.approx(70.0)
    assert adult.live_weight_cohort_potential_final == pytest.approx(70.0)
    assert adult.live_weight_cohort_at_slaughter == pytest.approx(70.0)

    average = calc_avg_weights(100.0, 300.0, 200.0, 0.4)
    assert average.live_weight_cohort_final == pytest.approx(260.0)
    assert average.live_weight_cohort_average == pytest.approx(180.0)
    assert calc_daily_weight_gain(300.0, 100.0, 100.0) == pytest.approx(2.0)
    assert calc_daily_weight_gain(100.0, 200.0, 100.0) == pytest.approx(-1.0)


def test_pinned_energy_reference_cases() -> None:
    cattle_work = calc_metabolic_energy_req_work(
        "CTL",
        "FA",
        15.0,
        draught_work_hours_female=2.0,
        draught_work_hours_male=4.0,
        draught_fraction_female=0.5,
        draught_fraction_male=0.3,
    )
    assert cattle_work == pytest.approx(0.1 * 15.0 * 2.0 * 0.5)

    camel_work = calc_metabolic_energy_req_work(
        "CML",
        "MA",
        18.0,
        draught_work_hours_female=2.0,
        draught_work_hours_male=6.0,
        draught_fraction_female=0.5,
        draught_fraction_male=0.4,
    )
    assert camel_work == pytest.approx(4.0 * 6.0 * 0.4)

    assert calc_metabolic_energy_req_fibre("SHP", "FA", 2.5) == pytest.approx(
        24.0 * 2.5 / 365.0
    )
    assert calc_metabolic_energy_req_fibre("CML", "FA", 3.0) == pytest.approx(
        (24.0 / 0.43) * (3.0 / 365.0)
    )

    cattle_pregnancy = calc_metabolic_energy_req_pregnancy(
        "CTL",
        "FA",
        metabolic_energy_req_maintenance=15.0,
        parturition_rate=0.8,
        litter_size=1.0,
        pregnancy_duration=283.0,
        non_productive_duration=10.0,
        lactation_duration=30.0,
        cohort_duration_days=730.0,
        offtake_rate=0.2,
    )
    assert cattle_pregnancy == pytest.approx(15.0 * 0.1 * 0.8 * 283.0 / 365.0)

    rem = calc_rem_maintenance("CTL", 0.65)
    expected_rem = 1.123 - (0.004092 * 65.0) + (0.00001126 * 65.0**2) - (25.4 / 65.0)
    assert rem == pytest.approx(expected_rem)

    reg = calc_reg_growth("GTS", 0.55)
    expected_reg = 1.164 - (0.005160 * 55.0) + (0.00001308 * 55.0**2) - (37.4 / 55.0)
    assert reg == pytest.approx(expected_reg)

    total = calc_total_metabolic_energy_req(
        species_short="CTL",
        metabolic_energy_req_maintenance=15.0,
        metabolic_energy_req_activity=3.0,
        metabolic_energy_req_lactation=8.0,
        metabolic_energy_req_work=0.0,
        metabolic_energy_req_pregnancy=1.5,
        net_energy_maintenance_digestible_energy_ratio=0.6,
        metabolic_energy_req_growth=0.0,
        metabolic_energy_req_fibre_production=0.0,
        metabolic_energy_req_egg_deposition=0.0,
        net_energy_growth_digestible_energy_ratio=0.5,
        ration_digestibility_fraction=0.65,
    )
    assert total == pytest.approx(((15.0 + 3.0 + 8.0 + 1.5) / 0.6) / 0.65)

    assert calc_ration_intake("CTL", 25.0, 18.5, 12.0) == pytest.approx(25.0 / 18.5)
    assert calc_ration_intake("PGS", 15.0, 18.0, 13.5) == pytest.approx(15.0 / 13.5)

    assert calc_rem_maintenance("PGS", 0.75) is None
    assert calc_reg_growth("CML", 0.60) is None
    assert math.isfinite(total)