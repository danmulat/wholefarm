import pytest

from wholefarm.gleam_cohort import CohortInputs, RationProfile
from wholefarm.gleam_core import ManureManagementSystem
from wholefarm.livestock_farm import (
    DietEmissionFactors,
    LivestockCohortSpec,
    calculate_feed_emissions,
    run_livestock_farm,
)


def _adult_cattle_spec() -> LivestockCohortSpec:
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
    feed = DietEmissionFactors(
        co2_fertilizer_g_kg_dm=25.0,
        co2_pesticides_g_kg_dm=1.0,
        co2_crop_activities_g_kg_dm=40.0,
        co2_luc_nopeat_g_kg_dm=0.0,
        co2_luc_peat_g_kg_dm=0.0,
        n2o_fertilizer_g_kg_dm=0.05,
        n2o_manure_applied_g_kg_dm=0.02,
        n2o_crop_residues_g_kg_dm=0.01,
        ch4_rice_g_kg_dm=0.0,
    )
    return LivestockCohortSpec(cohort, ration, systems, feed)


def test_feed_emission_conversion() -> None:
    factors = DietEmissionFactors(
        co2_fertilizer_g_kg_dm=100.0,
        co2_pesticides_g_kg_dm=0.0,
        co2_crop_activities_g_kg_dm=0.0,
        co2_luc_nopeat_g_kg_dm=0.0,
        co2_luc_peat_g_kg_dm=0.0,
        n2o_fertilizer_g_kg_dm=1.0,
        n2o_manure_applied_g_kg_dm=0.0,
        n2o_crop_residues_g_kg_dm=0.0,
        ch4_rice_g_kg_dm=0.0,
    )
    result = calculate_feed_emissions(1000.0, factors, 27.2, 273.0)
    assert result.co2_kg == pytest.approx(100.0)
    assert result.n2o_kg == pytest.approx(1.0)
    assert result.co2e_t == pytest.approx((100.0 + 273.0) / 1000.0)
    assert result.complete


def test_farm_aggregation_connects_gleam_cohorts() -> None:
    result = run_livestock_farm([_adult_cattle_spec()])
    assert result.enteric_ch4_kg > 0
    assert result.manure_ch4_kg > 0
    assert result.manure_n2o_kg > 0
    assert result.nitrogen_excretion_kg > 0
    assert result.volatile_solids_kg > 0
    assert result.milk_fpcm_kg > 0
    assert result.ghg.total_co2e_t > 0
    assert result.feed_emission_profile_complete


def test_missing_feed_profile_is_visible_not_silently_complete() -> None:
    spec = _adult_cattle_spec()
    missing = LivestockCohortSpec(
        inputs=spec.inputs,
        ration=spec.ration,
        manure_systems=spec.manure_systems,
        feed_emissions=None,
    )
    result = run_livestock_farm([missing])
    assert not result.feed_emission_profile_complete
    assert result.ghg.feed_production_co2e_t == 0.0
