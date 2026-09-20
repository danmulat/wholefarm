from datetime import date

import pytest
from pydantic import ValidationError

from wholefarm.input_adapters import enterprise_to_specs
from wholefarm.input_schema import (
    FarmSurvey,
    LandUnit,
    LivestockCohortRecord,
    LivestockEnterprise,
    ManureManagementRecord,
    RationProfileRecord,
)
from wholefarm.livestock_farm import run_livestock_farm


def _ration() -> RationProfileRecord:
    return RationProfileRecord(
        ration_id="dairy_ration",
        digestibility_fraction=0.62,
        gross_energy_mj_kg_dm=18.4,
        metabolizable_energy_mj_kg_dm=10.5,
        nitrogen_kg_kg_dm=0.025,
        urinary_energy_fraction=0.04,
        ash_fraction=0.08,
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


def _cohort() -> LivestockCohortRecord:
    return LivestockCohortRecord(
        cohort_id="adult_cows",
        ration_id="dairy_ration",
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
        litter_size=1,
        parturition_rate=0.8,
        live_weight_at_birth=30,
        live_weight_at_weaning=90,
        pregnancy_duration=283,
    )


def _manure() -> list[ManureManagementRecord]:
    return [
        ManureManagementRecord(
            system_id="mms_pasture",
            fraction=0.6,
            methane_conversion_factor_percent=0.47,
            bo_m3_ch4_per_kg_vs=0.19,
            n2o_ef3=0.02,
            n2o_ef4=0.01,
            nitrogen_fracgas=0.21,
            n2o_ef5=0.011,
            nitrogen_fracleach=0.24,
        ),
        ManureManagementRecord(
            system_id="mms_solid",
            fraction=0.4,
            methane_conversion_factor_percent=5,
            bo_m3_ch4_per_kg_vs=0.13,
            n2o_ef3=0.005,
            n2o_ef4=0.01,
            nitrogen_fracgas=0.45,
            n2o_ef5=0.011,
            nitrogen_fracleach=0.02,
        ),
    ]


def test_enterprise_adapter_runs_gleam_farm_chain() -> None:
    enterprise = LivestockEnterprise(
        enterprise_id="dairy",
        rations=[_ration()],
        manure_systems=_manure(),
        cohorts=[_cohort()],
    )
    specs = enterprise_to_specs(enterprise)
    result = run_livestock_farm(specs)
    assert result.enteric_ch4_kg > 0
    assert result.nitrogen_excretion_kg > 0
    assert result.feed_emission_profile_complete


def test_enterprise_rejects_unknown_ration_reference() -> None:
    cohort = _cohort().model_copy(update={"ration_id": "missing"})
    with pytest.raises(ValidationError):
        LivestockEnterprise(
            enterprise_id="dairy",
            rations=[_ration()],
            manure_systems=_manure(),
            cohorts=[cohort],
        )


def test_farm_survey_accepts_livestock_enterprise() -> None:
    enterprise = LivestockEnterprise(
        enterprise_id="dairy",
        rations=[_ration()],
        manure_systems=_manure(),
        cohorts=[_cohort()],
    )
    survey = FarmSurvey(
        farm_id="farm_1",
        country="Kenya",
        basin="Lake Victoria Basin",
        survey_date=date(2026, 9, 20),
        land_units=[LandUnit(land_unit_id="field_1", area_ha=2.0, land_use="mixed_crop")],
        livestock_enterprises=[enterprise],
    )
    assert survey.livestock_enterprises[0].cohorts[0].species_short == "CTL"
