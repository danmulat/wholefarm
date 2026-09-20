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
