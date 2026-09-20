"""Adapters from validated farm survey records to calculation dataclasses."""

from __future__ import annotations

from .gleam_cohort import CohortInputs, RationProfile
from .gleam_core import ManureManagementSystem
from .input_schema import (
    LivestockCohortRecord,
    FarmSurvey,
    LivestockEnterprise,
    ManureManagementRecord,
    RationProfileRecord,
)
from .livestock_farm import DietEmissionFactors, LivestockCohortSpec


def ration_record_to_profile(record: RationProfileRecord) -> RationProfile:
    return RationProfile(
        digestibility_fraction=record.digestibility_fraction,
        gross_energy_mj_kg_dm=record.gross_energy_mj_kg_dm,
        metabolizable_energy_mj_kg_dm=record.metabolizable_energy_mj_kg_dm,
        nitrogen_kg_kg_dm=record.nitrogen_kg_kg_dm,
        urinary_energy_fraction=record.urinary_energy_fraction,
        ash_fraction=record.ash_fraction,
    )


def ration_record_to_feed_emissions(
    record: RationProfileRecord,
) -> DietEmissionFactors | None:
    values = (
        record.co2_fertilizer_g_kg_dm,
        record.co2_pesticides_g_kg_dm,
        record.co2_crop_activities_g_kg_dm,
        record.co2_luc_nopeat_g_kg_dm,
        record.co2_luc_peat_g_kg_dm,
        record.n2o_fertilizer_g_kg_dm,
        record.n2o_manure_applied_g_kg_dm,
        record.n2o_crop_residues_g_kg_dm,
        record.ch4_rice_g_kg_dm,
    )
    if all(value is None for value in values):
        return None
    return DietEmissionFactors(
        co2_fertilizer_g_kg_dm=record.co2_fertilizer_g_kg_dm,
        co2_pesticides_g_kg_dm=record.co2_pesticides_g_kg_dm,
        co2_crop_activities_g_kg_dm=record.co2_crop_activities_g_kg_dm,
        co2_luc_nopeat_g_kg_dm=record.co2_luc_nopeat_g_kg_dm,
        co2_luc_peat_g_kg_dm=record.co2_luc_peat_g_kg_dm,
        n2o_fertilizer_g_kg_dm=record.n2o_fertilizer_g_kg_dm,
        n2o_manure_applied_g_kg_dm=record.n2o_manure_applied_g_kg_dm,
        n2o_crop_residues_g_kg_dm=record.n2o_crop_residues_g_kg_dm,
        ch4_rice_g_kg_dm=record.ch4_rice_g_kg_dm,
    )


def manure_record_to_system(
    record: ManureManagementRecord,
) -> ManureManagementSystem:
    return ManureManagementSystem(
        fraction=record.fraction,
        methane_conversion_factor_percent=record.methane_conversion_factor_percent,
        bo_m3_ch4_per_kg_vs=record.bo_m3_ch4_per_kg_vs,
        n2o_ef3=record.n2o_ef3,
        n2o_ef4=record.n2o_ef4,
        nitrogen_fracgas=record.nitrogen_fracgas,
        n2o_ef5=record.n2o_ef5,
        nitrogen_fracleach=record.nitrogen_fracleach,
    )


def manure_records_to_systems(
    records: list[ManureManagementRecord],
) -> dict[str, ManureManagementSystem]:
    systems = {record.system_id: manure_record_to_system(record) for record in records}
    if len(systems) != len(records):
        raise ValueError("system_id values must be unique within an enterprise")
    return systems


def cohort_record_to_inputs(record: LivestockCohortRecord) -> CohortInputs:
    values = record.model_dump(exclude={"cohort_id", "ration_id"})
    return CohortInputs(**values)


def enterprise_to_specs(
    enterprise: LivestockEnterprise,
) -> list[LivestockCohortSpec]:
    rations = {record.ration_id: record for record in enterprise.rations}
    manure_systems = manure_records_to_systems(enterprise.manure_systems)
    result: list[LivestockCohortSpec] = []
    for cohort in enterprise.cohorts:
        ration_record = rations[cohort.ration_id]
        result.append(
            LivestockCohortSpec(
                inputs=cohort_record_to_inputs(cohort),
                ration=ration_record_to_profile(ration_record),
                manure_systems=manure_systems,
                feed_emissions=ration_record_to_feed_emissions(ration_record),
            )
        )
    return result


def farm_survey_to_livestock_specs(
    survey: FarmSurvey,
) -> list[LivestockCohortSpec]:
    specs: list[LivestockCohortSpec] = []
    for enterprise in survey.livestock_enterprises:
        specs.extend(enterprise_to_specs(enterprise))
    return specs
