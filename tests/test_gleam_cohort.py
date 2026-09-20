import pytest

from wholefarm.gleam_cohort import CohortInputs, RationProfile, run_gleam_cohort
from wholefarm.gleam_core import ManureManagementSystem


def test_connected_cattle_cohort_chain() -> None:
    cohort = CohortInputs(
        species_short="CTL",
        cohort_short="FA",
        cohort_stock_size=20,
        simulation_duration_days=365,
        live_weight_cohort_average=450,
        live_weight_cohort_initial=450,
        live_weight_cohort_final=450,
        live_weight_mature_stage=450,
        live_weight_cohort_at_slaughter=450,
        cohort_duration_days=365,
        offtake_rate=0.1,
        offtake_heads_assessment=2,
        low_activity_fraction=0.6,
        high_activity_fraction=0.2,
        lactating_females_fraction=0.7,
        milk_yield_day=8,
        milk_protein_fraction=0.033,
        milk_fat_fraction=0.04,
        milk_lactose_fraction=0.048,
        litter_size=1,
        parturition_rate=0.8,
        live_weight_at_birth=30,
        live_weight_at_weaning=90,
        pregnancy_duration=283,
    )
    ration = RationProfile(
        digestibility_fraction=0.62,
        gross_energy_mj_kg_dm=18.4,
        metabolizable_energy_mj_kg_dm=10.5,
        nitrogen_kg_kg_dm=0.025,
        urinary_energy_fraction=0.04,
        ash_fraction=0.08,
    )
    systems = {
        "mms_pasture": ManureManagementSystem(
            fraction=0.6,
            methane_conversion_factor_percent=0.47,
            bo_m3_ch4_per_kg_vs=0.19,
            n2o_ef3=0.02,
            n2o_ef4=0.01,
            nitrogen_fracgas=0.21,
            n2o_ef5=0.011,
            nitrogen_fracleach=0.24,
        ),
        "mms_solid": ManureManagementSystem(
            fraction=0.4,
            methane_conversion_factor_percent=5,
            bo_m3_ch4_per_kg_vs=0.13,
            n2o_ef3=0.005,
            n2o_ef4=0.01,
            nitrogen_fracgas=0.45,
            n2o_ef5=0.011,
            nitrogen_fracleach=0.02,
        ),
    }

    result = run_gleam_cohort(cohort, ration, systems)

    assert result.ration_intake_kg_dm_head_day > 0
    assert result.energy.total_mj_head_day > result.energy.maintenance_mj_head_day
    assert result.nitrogen.intake_kg_n_head_day > result.nitrogen.retention_kg_n_head_day
    assert result.emissions.enteric_ch4_kg_head_day > 0
    assert result.emissions.volatile_solids_kg_head_day > 0
    assert result.production.milk.mass_kg == pytest.approx(8 * 365 * 20 * 0.7)
    assert result.totals.enteric_ch4_kg == pytest.approx(
        result.emissions.enteric_ch4_kg_head_day * 20 * 365
    )


def test_juvenile_cattle_has_zero_enteric_ym_under_pinned_gleam_rule() -> None:
    cohort = CohortInputs(
        species_short="CTL",
        cohort_short="FJ",
        cohort_stock_size=10,
        simulation_duration_days=365,
        live_weight_cohort_average=60,
        live_weight_cohort_initial=30,
        live_weight_cohort_final=90,
        live_weight_mature_stage=450,
        live_weight_cohort_at_slaughter=90,
        cohort_duration_days=180,
        offtake_rate=0.05,
        low_activity_fraction=0.5,
        high_activity_fraction=0.2,
        live_weight_at_birth=30,
        live_weight_at_weaning=90,
    )
    ration = RationProfile(0.65, 18.4, 10.5, 0.025, 0.04, 0.08)
    systems = {
        "mms_pasture": ManureManagementSystem(
            fraction=1.0,
            methane_conversion_factor_percent=0.47,
            bo_m3_ch4_per_kg_vs=0.19,
            n2o_ef3=0.02,
            n2o_ef4=0.01,
            nitrogen_fracgas=0.21,
            n2o_ef5=0.011,
            nitrogen_fracleach=0.24,
        )
    }

    result = run_gleam_cohort(cohort, ration, systems)

    assert result.emissions.ym_percent == 0
    assert result.emissions.enteric_ch4_kg_head_day == 0
