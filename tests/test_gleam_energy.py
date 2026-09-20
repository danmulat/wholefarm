import pytest

from wholefarm.gleam_energy import (
    calc_metabolic_energy_req_activity,
    calc_metabolic_energy_req_fibre,
    calc_metabolic_energy_req_growth,
    calc_metabolic_energy_req_lactation,
    calc_metabolic_energy_req_maintenance,
    calc_metabolic_energy_req_pregnancy,
    calc_metabolic_energy_req_work,
    calc_ration_intake,
    calc_reg_growth,
    calc_rem_maintenance,
    calc_total_metabolic_energy_req,
)


def test_cattle_maintenance_reference_formula() -> None:
    value = calc_metabolic_energy_req_maintenance(
        "CTL",
        "FA",
        500.0,
        lactating_females_fraction=0.7,
    )
    coefficient = 0.386 * 0.7 + 0.322 * 0.3
    assert value == pytest.approx(coefficient * 500.0**0.75)


def test_sheep_maintenance_reference_formula() -> None:
    value = calc_metabolic_energy_req_maintenance(
        "SHP",
        "FS",
        40.0,
        age_first_parturition=400,
    )
    expected = 40.0**0.75 * (
        0.236 * (365.0 / 400.0)
        + 0.217 * ((400.0 - 365.0) / 400.0)
    )
    assert value == pytest.approx(expected)


def test_activity_energy_reference_cases() -> None:
    cattle = calc_metabolic_energy_req_activity(
        "CTL",
        "FA",
        metabolic_energy_req_maintenance=15.0,
        live_weight_cohort_average=500,
        low_activity_fraction=0.6,
        high_activity_fraction=0.2,
    )
    assert cattle == pytest.approx(((0.17 * 0.6) + (0.36 * 0.2)) * 15.0)

    camel = calc_metabolic_energy_req_activity(
        "CML",
        "FA",
        metabolic_energy_req_maintenance=12.0,
        live_weight_cohort_average=400,
        low_activity_fraction=0.5,
        high_activity_fraction=0.0,
    )
    assert camel == pytest.approx((0.1 * 0.5) * 12.0)

    pig = calc_metabolic_energy_req_activity(
        "PGS",
        "FA",
        metabolic_energy_req_maintenance=10.0,
        live_weight_cohort_average=150,
        low_activity_fraction=0.5,
        high_activity_fraction=0.3,
    )
    assert pig == pytest.approx(0.125 * (0.5 + 0.3) * 10.0)


def test_growth_energy_reference_cases() -> None:
    cattle = calc_metabolic_energy_req_growth(
        "CTL",
        "FJ",
        live_weight_cohort_average=200,
        live_weight_cohort_final=300,
        live_weight_cohort_initial=150,
        live_weight_mature_stage=500,
        daily_weight_gain=0.5,
        offtake_rate=0.1,
        cohort_duration_days=100,
    )
    expected_cattle = 22.02 * ((200 / (0.8 * 500)) ** 0.75) * (0.5**1.097)
    assert cattle == pytest.approx(expected_cattle)

    sheep = calc_metabolic_energy_req_growth(
        "SHP",
        "FJ",
        live_weight_cohort_average=30,
        live_weight_cohort_final=50,
        live_weight_cohort_initial=25,
        live_weight_mature_stage=60,
        daily_weight_gain=0.1,
        offtake_rate=0.1,
        cohort_duration_days=250,
    )
    expected_sheep = ((50 - 25) * (2.1 + 0.5 * 0.45 * (25 + 50))) / 250
    assert sheep == pytest.approx(expected_sheep)

    pig = calc_metabolic_energy_req_growth(
        "PGS",
        "FJ",
        live_weight_cohort_average=50,
        live_weight_cohort_final=80,
        live_weight_cohort_initial=40,
        live_weight_mature_stage=300,
        daily_weight_gain=0.3,
        offtake_rate=0.1,
        cohort_duration_days=133,
    )
    cgro = 0.65 * 0.23 * 54 + (1 - 0.65) * 0.9 * 52.3
    assert pig == pytest.approx(0.3 * cgro)
    assert calc_metabolic_energy_req_growth("CTL", "FA", daily_weight_gain=0) == 0


def test_lactation_energy_reference_cases() -> None:
    cattle = calc_metabolic_energy_req_lactation(
        "CTL",
        "FA",
        lactating_females_fraction=0.8,
        milk_yield_day=20,
        milk_fat_fraction=0.04,
        non_productive_duration=0,
        pregnancy_duration=0,
        litter_size=1,
        death_rate_juvenile=0,
        live_weight_at_birth=35,
        live_weight_at_weaning=90,
        lactation_duration=0,
        parturition_rate=0.8,
    )
    expected_cattle = (
        (20 * 0.8) + (0.8 * 5 * (90 - 35) / 365)
    ) * (0.04 * 100 * 0.40 + 1.47)
    assert cattle == pytest.approx(expected_cattle)

    sheep = calc_metabolic_energy_req_lactation(
        "SHP",
        "FA",
        lactating_females_fraction=0.9,
        milk_yield_day=1.5,
        milk_fat_fraction=0.06,
        non_productive_duration=0,
        pregnancy_duration=0,
        litter_size=1.5,
        death_rate_juvenile=0,
        live_weight_at_birth=4,
        live_weight_at_weaning=18,
        lactation_duration=0,
        parturition_rate=1.2,
    )
    expected_sheep = (
        (1.5 * 0.9) + (1.5 * 1.2 * 5 * (18 - 4) / 365)
    ) * 4.6
    assert sheep == pytest.approx(expected_sheep)

    pig = calc_metabolic_energy_req_lactation(
        "PGS",
        "FA",
        lactating_females_fraction=0,
        milk_yield_day=0,
        milk_fat_fraction=0,
        non_productive_duration=0.2,
        pregnancy_duration=0.3,
        litter_size=10,
        death_rate_juvenile=0.1,
        live_weight_at_birth=1.5,
        live_weight_at_weaning=8,
        lactation_duration=0.5,
        parturition_rate=2.2,
    )
    cadj = 0.5 / (0.2 + 0.3 + 0.5)
    expected_pig = (
        10
        * (1 - 0.5 * 0.1)
        * ((0.02059 * (8 - 1.5) * 1000 / 0.5) - (0.3766 / 0.67))
        * cadj
    )
    assert pig == pytest.approx(expected_pig)


def test_work_energy_reference_rules() -> None:
    cattle = calc_metabolic_energy_req_work(
        "CTL",
        "MA",
        metabolic_energy_req_maintenance=20.0,
        draught_work_hours_male=4,
        draught_fraction_male=0.3,
    )
    assert cattle == pytest.approx(0.1 * 20.0 * 4 * 0.3)

    camel = calc_metabolic_energy_req_work(
        "CML",
        "MA",
        metabolic_energy_req_maintenance=18.0,
        draught_work_hours_male=6,
        draught_fraction_male=0.4,
    )
    assert camel == pytest.approx(4 * 6 * 0.4)


def test_fibre_energy_reference_rules() -> None:
    assert calc_metabolic_energy_req_fibre("SHP", "FA", 2.5) == pytest.approx(
        24 * 2.5 / 365
    )
    assert calc_metabolic_energy_req_fibre("CML", "FA", 3.0) == pytest.approx(
        (24 / 0.43) * 3.0 / 365
    )
    assert calc_metabolic_energy_req_fibre("CTL", "FA", 1.0) == 0


def test_pregnancy_energy_reference_cases() -> None:
    cattle = calc_metabolic_energy_req_pregnancy(
        "CTL",
        "FA",
        metabolic_energy_req_maintenance=15.0,
        parturition_rate=0.8,
        litter_size=1,
        pregnancy_duration=283,
        non_productive_duration=10,
        lactation_duration=30,
        cohort_duration_days=730,
        offtake_rate=0.2,
    )
    assert cattle == pytest.approx(15.0 * 0.1 * 0.8 * 283 / 365)

    sheep = calc_metabolic_energy_req_pregnancy(
        "SHP",
        "FA",
        metabolic_energy_req_maintenance=8.0,
        parturition_rate=1.2,
        litter_size=1.5,
        pregnancy_duration=152,
        non_productive_duration=10,
        lactation_duration=30,
        cohort_duration_days=700,
        offtake_rate=0.1,
    )
    cpreg = 0.077 * 0.5 + 0.126 * 0.5
    assert sheep == pytest.approx(8.0 * cpreg * 1.2 * 152 / 365)

    pig = calc_metabolic_energy_req_pregnancy(
        "PGS",
        "FA",
        metabolic_energy_req_maintenance=12.0,
        parturition_rate=2.2,
        litter_size=10,
        pregnancy_duration=115,
        non_productive_duration=10,
        lactation_duration=30,
        cohort_duration_days=365,
        offtake_rate=0.1,
    )
    assert pig == pytest.approx(0.14985 * 10 * 115 / (10 + 115 + 30))


def test_rem_and_reg_reference_formulas() -> None:
    digestibility = 0.6
    de = 60.0
    rem_expected = 1.123 - 0.004092 * de + 0.00001126 * de**2 - 25.4 / de
    reg_expected = 1.164 - 0.005160 * de + 0.00001308 * de**2 - 37.4 / de
    assert calc_rem_maintenance("CTL", digestibility) == pytest.approx(rem_expected)
    assert calc_reg_growth("CTL", digestibility) == pytest.approx(reg_expected)


def test_total_energy_and_ration_intake_cattle() -> None:
    digestibility = 0.65
    rem = calc_rem_maintenance("CTL", digestibility)
    reg = calc_reg_growth("CTL", digestibility)
    total = calc_total_metabolic_energy_req(
        "CTL",
        metabolic_energy_req_maintenance=30,
        metabolic_energy_req_activity=2,
        metabolic_energy_req_lactation=8,
        metabolic_energy_req_work=1,
        metabolic_energy_req_pregnancy=2,
        net_energy_maintenance_digestible_energy_ratio=rem,
        metabolic_energy_req_growth=4,
        metabolic_energy_req_fibre_production=0,
        metabolic_energy_req_egg_deposition=0,
        net_energy_growth_digestible_energy_ratio=reg,
        ration_digestibility_fraction=digestibility,
    )
    expected = ((30 + 2 + 8 + 1 + 2) / rem + 4 / reg) / digestibility
    assert total == pytest.approx(expected)
    assert calc_ration_intake("CTL", total, 18.4, 10.5) == pytest.approx(total / 18.4)


def test_ration_intake_uses_metabolizable_energy_for_camel() -> None:
    assert calc_ration_intake("CML", 80, 18.4, 10.0) == 8.0
