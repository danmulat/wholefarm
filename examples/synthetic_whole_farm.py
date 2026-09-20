"""Runnable synthetic example connecting the whole farm calculation modules.

All activity data and emission factors in this example are synthetic and are
only for software testing. They are not project measurements.
"""

from __future__ import annotations

import json

from wholefarm.farm_pipeline import FarmScenarioInputs, compare_farm_scenarios
from wholefarm.gleam_cohort import CohortInputs, RationProfile
from wholefarm.gleam_core import ManureManagementSystem
from wholefarm.livestock_farm import (
    DietEmissionFactors,
    LivestockCohortSpec,
    run_livestock_farm,
)
from wholefarm.nutrient_flow import ManureRecoveryConfig, route_manure_to_fields
from wholefarm.rothc import RothCPools
from wholefarm.rothc_scenario import (
    MonthlyClimate,
    build_rothc_year,
    distribute_annual_carbon,
    repeat_rothc_year,
    run_rothc_baseline_intervention,
)
from wholefarm.soil_ghg import SoilN2OFactors, SoilNitrogenSource, calculate_soil_n2o


def cattle_spec(ch4_mitigation_factor: float) -> LivestockCohortSpec:
    inputs = CohortInputs(
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
        ch4_mitigation_factor=ch4_mitigation_factor,
    )
    ration = RationProfile(0.62, 18.4, 10.5, 0.025, 0.04, 0.08)
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
            methane_conversion_factor_percent=5.0,
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
    return LivestockCohortSpec(inputs, ration, systems, feed)


def climate_year() -> tuple[MonthlyClimate, ...]:
    rainfall = (40, 55, 90, 130, 120, 70, 45, 55, 85, 120, 95, 50)
    return tuple(
        MonthlyClimate(
            temperature_c=20.0,
            rainfall_mm=float(rainfall[index]),
            open_pan_evaporation_mm=90.0,
            plant_cover=1,
        )
        for index in range(12)
    )


def main() -> None:
    area_ha = 5.0
    baseline_livestock = run_livestock_farm([cattle_spec(1.0)])
    intervention_livestock = run_livestock_farm([cattle_spec(0.9)])

    baseline_recovery = route_manure_to_fields(
        baseline_livestock.nitrogen_excretion_kg,
        baseline_livestock.volatile_solids_kg,
        ManureRecoveryConfig(0.35, 0.70, 0.80, 0.65, 0.50),
    )
    intervention_recovery = route_manure_to_fields(
        intervention_livestock.nitrogen_excretion_kg,
        intervention_livestock.volatile_solids_kg,
        ManureRecoveryConfig(0.80, 0.80, 0.90, 0.75, 0.50),
    )

    plant_c = distribute_annual_carbon(4.0, [1.0 / 12.0] * 12)
    baseline_manure_c = distribute_annual_carbon(
        baseline_recovery.field_applied_c_t_ha(area_ha),
        [1.0 / 12.0] * 12,
    )
    intervention_manure_c = distribute_annual_carbon(
        intervention_recovery.field_applied_c_t_ha(area_ha),
        [1.0 / 12.0] * 12,
    )
    baseline_year = build_rothc_year(climate_year(), plant_c, baseline_manure_c, 1.44)
    intervention_year = build_rothc_year(
        climate_year(),
        plant_c,
        intervention_manure_c,
        1.44,
    )
    initial_pools = RothCPools(1.0, 4.0, 1.0, 20.0, 4.0)
    baseline_soc, intervention_soc = run_rothc_baseline_intervention(
        initial_pools,
        repeat_rothc_year(baseline_year, 5),
        repeat_rothc_year(intervention_year, 5),
        clay_percent=30.0,
        depth_cm=30.0,
        area_ha=area_ha,
    )

    soil_factors = SoilN2OFactors(0.01, 0.011)
    baseline_soil = calculate_soil_n2o(
        [
            SoilNitrogenSource("mineral", 250.0, 0.01, 0.10, 0.20),
            SoilNitrogenSource(
                "recovered_manure",
                baseline_recovery.field_applied_n_kg,
                0.01,
                0.20,
                0.10,
            ),
        ],
        soil_factors,
    )
    intervention_soil = calculate_soil_n2o(
        [
            SoilNitrogenSource("mineral", 180.0, 0.01, 0.10, 0.20),
            SoilNitrogenSource(
                "recovered_manure",
                intervention_recovery.field_applied_n_kg,
                0.01,
                0.20,
                0.10,
            ),
        ],
        soil_factors,
    )

    baseline_inputs = FarmScenarioInputs(
        scenario_name="baseline",
        livestock=baseline_livestock,
        area_ha=area_ha,
        initial_soc_t_c_ha=baseline_soc.initial_soc_t_c_ha,
        final_soc_t_c_ha=baseline_soc.final_soc_t_c_ha,
        soil_n2o_co2e_t=baseline_soil.total_co2e_t,
    )
    intervention_inputs = FarmScenarioInputs(
        scenario_name="intervention",
        livestock=intervention_livestock,
        area_ha=area_ha,
        initial_soc_t_c_ha=intervention_soc.initial_soc_t_c_ha,
        final_soc_t_c_ha=intervention_soc.final_soc_t_c_ha,
        soil_n2o_co2e_t=intervention_soil.total_co2e_t,
    )
    comparison = compare_farm_scenarios(baseline_inputs, intervention_inputs)

    summary = {
        "baseline_net_t_co2e": comparison.baseline.net_co2e_t,
        "intervention_net_t_co2e": comparison.intervention.net_co2e_t,
        "gross_emission_reduction_t_co2e": comparison.gross_emission_reduction_co2e_t,
        "additional_removals_t_co2e": comparison.additional_removals_co2e_t,
        "total_climate_benefit_t_co2e": comparison.total_climate_benefit_co2e_t,
        "baseline_final_soc_t_c_ha": baseline_soc.final_soc_t_c_ha,
        "intervention_final_soc_t_c_ha": intervention_soc.final_soc_t_c_ha,
        "intervention_manure_n_to_field_kg": intervention_recovery.field_applied_n_kg,
        "feed_emission_profile_complete": (
            intervention_livestock.feed_emission_profile_complete
        ),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
