from wholefarm.gleam_energy import (
    calc_metabolic_energy_req_maintenance,
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
        lactating_females_fraction=0.8,
    )
    coefficient = 0.386 * 0.8 + 0.322 * 0.2
    assert abs(value - coefficient * 500.0**0.75) < 1e-12


def test_rem_and_reg_reference_formulas() -> None:
    digestibility = 0.6
    de = 60.0
    rem_expected = 1.123 - 0.004092 * de + 0.00001126 * de**2 - 25.4 / de
    reg_expected = 1.164 - 0.005160 * de + 0.00001308 * de**2 - 37.4 / de
    assert abs(calc_rem_maintenance("CTL", digestibility) - rem_expected) < 1e-12
    assert abs(calc_reg_growth("CTL", digestibility) - reg_expected) < 1e-12


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
    assert abs(total - expected) < 1e-12
    assert calc_ration_intake("CTL", total, 18.4, 10.5) == total / 18.4


def test_ration_intake_uses_metabolizable_energy_for_camel() -> None:
    assert calc_ration_intake("CML", 80, 18.4, 10.0) == 8.0


def test_activity_energy_reference_rules() -> None:
    from wholefarm.gleam_energy import calc_metabolic_energy_req_activity

    cattle = calc_metabolic_energy_req_activity(
        "CTL",
        "FA",
        metabolic_energy_req_maintenance=30,
        live_weight_cohort_average=500,
        low_activity_fraction=0.75,
        high_activity_fraction=0.25,
    )
    assert cattle == (0.17 * 0.75 + 0.36 * 0.25) * 30

    sheep = calc_metabolic_energy_req_activity(
        "SHP",
        "FA",
        metabolic_energy_req_maintenance=10,
        live_weight_cohort_average=50,
        low_activity_fraction=0.5,
        high_activity_fraction=0.5,
    )
    assert sheep == (0.0107 * 0.5 + 0.024 * 0.5) * 50


def test_work_energy_reference_rules() -> None:
    from wholefarm.gleam_energy import calc_metabolic_energy_req_work

    cattle = calc_metabolic_energy_req_work(
        "CTL",
        "MA",
        metabolic_energy_req_maintenance=40,
        draught_work_hours_male=3,
        draught_fraction_male=0.5,
    )
    assert cattle == 0.1 * 40 * 3 * 0.5

    camel = calc_metabolic_energy_req_work(
        "CML",
        "FA",
        metabolic_energy_req_maintenance=40,
        draught_work_hours_female=4,
        draught_fraction_female=0.25,
    )
    assert camel == 4 * 4 * 0.25


def test_fibre_energy_reference_rules() -> None:
    from wholefarm.gleam_energy import calc_metabolic_energy_req_fibre

    assert calc_metabolic_energy_req_fibre("SHP", "FA", 5) == 24 * 5 / 365
    assert calc_metabolic_energy_req_fibre("CML", "FA", 5) == (24 / 0.43) * 5 / 365
    assert calc_metabolic_energy_req_fibre("CTL", "FA", 5) == 0
