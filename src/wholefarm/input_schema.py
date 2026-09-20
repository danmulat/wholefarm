"""Input schemas for farm surveys, soil observations and management records."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from .soc_stock import VM0042_MINIMUM_SOC_DEPTH_CM


class SoilLayerObservation(BaseModel):
    depth_top_cm: float = Field(ge=0.0)
    depth_bottom_cm: float = Field(gt=0.0)
    soc_g_kg: float = Field(ge=0.0)
    bulk_density_g_cm3: float | None = Field(default=None, gt=0.0)
    coarse_fragment_percent: float = Field(default=0.0, ge=0.0, lt=100.0)
    soc_method: str | None = None
    bulk_density_method: str | None = None

    @model_validator(mode="after")
    def validate_depth_interval(self) -> SoilLayerObservation:
        if self.depth_bottom_cm <= self.depth_top_cm:
            raise ValueError("depth_bottom_cm must be greater than depth_top_cm")
        return self


class SoilProfile(BaseModel):
    profile_id: str
    farm_id: str
    land_unit_id: str
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    sample_date: date
    land_use: str
    purpose: Literal["quantification", "calibration_validation"] = "quantification"
    extrapolation_method: str | None = None
    layers: list[SoilLayerObservation]

    @model_validator(mode="after")
    def validate_profile_depth(self) -> SoilProfile:
        if not self.layers:
            raise ValueError("At least one soil layer is required")
        ordered = sorted(self.layers, key=lambda layer: layer.depth_top_cm)
        if abs(ordered[0].depth_top_cm) > 1e-9:
            raise ValueError("Soil profile must begin at the soil surface")

        previous_bottom = 0.0
        for layer in ordered:
            if abs(layer.depth_top_cm - previous_bottom) > 1e-9:
                raise ValueError("Soil profile layers must be contiguous and nonoverlapping")
            previous_bottom = layer.depth_bottom_cm

        if self.purpose == "quantification":
            if previous_bottom < VM0042_MINIMUM_SOC_DEPTH_CM:
                raise ValueError("VM0042 quantification soil profiles must reach at least 30 cm")
        elif (
            previous_bottom < VM0042_MINIMUM_SOC_DEPTH_CM
            and not self.extrapolation_method
        ):
            raise ValueError(
                "Shallower calibration or validation profiles require an extrapolation method"
            )
        return self

    @property
    def sampled_depth_cm(self) -> float:
        return max(layer.depth_bottom_cm for layer in self.layers)


class LandManagementRecord(BaseModel):
    year: int = Field(ge=1900, le=2200)
    land_use: str
    crop_or_forage: str | None = None
    mineral_n_kg_ha: float = Field(default=0.0, ge=0.0)
    organic_n_kg_ha: float = Field(default=0.0, ge=0.0)
    plant_c_input_t_ha: float = Field(default=0.0, ge=0.0)
    manure_c_input_t_ha: float = Field(default=0.0, ge=0.0)
    residue_retained_fraction: float | None = Field(default=None, ge=0.0, le=1.0)
    cover_crop: bool | None = None
    irrigation: bool | None = None
    grazing_days: float | None = Field(default=None, ge=0.0)
    stocking_rate_lsu_ha: float | None = Field(default=None, ge=0.0)
    tree_density_ha: float | None = Field(default=None, ge=0.0)
    tillage_class: str | None = None


class LandUnit(BaseModel):
    land_unit_id: str
    area_ha: float = Field(gt=0.0)
    land_use: str
    management: list[LandManagementRecord] = Field(default_factory=list)


class RationProfileRecord(BaseModel):
    ration_id: str
    digestibility_fraction: float = Field(ge=0.0, le=1.0)
    gross_energy_mj_kg_dm: float = Field(gt=0.0)
    metabolizable_energy_mj_kg_dm: float = Field(gt=0.0)
    nitrogen_kg_kg_dm: float = Field(ge=0.0)
    urinary_energy_fraction: float = Field(ge=0.0, le=1.0)
    ash_fraction: float = Field(ge=0.0, le=1.0)
    co2_fertilizer_g_kg_dm: float | None = Field(default=None, ge=0.0)
    co2_pesticides_g_kg_dm: float | None = Field(default=None, ge=0.0)
    co2_crop_activities_g_kg_dm: float | None = Field(default=None, ge=0.0)
    co2_luc_nopeat_g_kg_dm: float | None = Field(default=None, ge=0.0)
    co2_luc_peat_g_kg_dm: float | None = Field(default=None, ge=0.0)
    n2o_fertilizer_g_kg_dm: float | None = Field(default=None, ge=0.0)
    n2o_manure_applied_g_kg_dm: float | None = Field(default=None, ge=0.0)
    n2o_crop_residues_g_kg_dm: float | None = Field(default=None, ge=0.0)
    ch4_rice_g_kg_dm: float | None = Field(default=None, ge=0.0)


class ManureManagementRecord(BaseModel):
    system_id: str
    fraction: float = Field(ge=0.0, le=1.0)
    methane_conversion_factor_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    bo_m3_ch4_per_kg_vs: float = Field(default=0.0, ge=0.0)
    n2o_ef3: float = Field(default=0.0, ge=0.0)
    n2o_ef4: float = Field(default=0.0, ge=0.0)
    nitrogen_fracgas: float = Field(default=0.0, ge=0.0, le=1.0)
    n2o_ef5: float = Field(default=0.0, ge=0.0)
    nitrogen_fracleach: float = Field(default=0.0, ge=0.0, le=1.0)


class LivestockCohortRecord(BaseModel):
    cohort_id: str
    ration_id: str
    species_short: Literal["CTL", "BFL", "SHP", "GTS", "PGS", "CML"]
    cohort_short: Literal["FJ", "FS", "FA", "MJ", "MS", "MA"]
    cohort_stock_size: float = Field(ge=0.0)
    simulation_duration_days: float = Field(gt=0.0)
    live_weight_cohort_average: float = Field(ge=0.0)
    live_weight_cohort_initial: float = Field(ge=0.0)
    live_weight_cohort_final: float = Field(ge=0.0)
    live_weight_mature_stage: float = Field(ge=0.0)
    live_weight_cohort_at_slaughter: float = Field(ge=0.0)
    cohort_duration_days: float = Field(gt=0.0)
    offtake_rate: float = Field(ge=0.0, le=1.0)
    offtake_heads_assessment: float = Field(default=0.0, ge=0.0)
    low_activity_fraction: float = Field(default=0.0, ge=0.0, le=1.0)
    high_activity_fraction: float = Field(default=0.0, ge=0.0, le=1.0)
    age_first_parturition: float | None = Field(default=None, ge=0.0)
    lactating_females_fraction: float = Field(default=0.0, ge=0.0, le=1.0)
    milk_yield_day: float = Field(default=0.0, ge=0.0)
    milk_protein_fraction: float = Field(default=0.033, ge=0.0, le=1.0)
    milk_fat_fraction: float = Field(default=0.04, ge=0.0, le=1.0)
    milk_lactose_fraction: float = Field(default=0.048, ge=0.0, le=1.0)
    fibre_yield_year: float = Field(default=0.0, ge=0.0)
    litter_size: float = Field(default=1.0, ge=0.0)
    parturition_rate: float = Field(default=0.0, ge=0.0)
    live_weight_at_birth: float = Field(default=0.0, ge=0.0)
    live_weight_at_weaning: float = Field(default=0.0, ge=0.0)
    pregnancy_duration: float = Field(default=0.0, ge=0.0)
    non_productive_duration: float = Field(default=0.0, ge=0.0)
    lactation_duration: float = Field(default=0.0, ge=0.0)
    death_rate_juvenile: float = Field(default=0.0, ge=0.0, le=1.0)
    draught_work_hours_female: float = Field(default=0.0, ge=0.0)
    draught_work_hours_male: float = Field(default=0.0, ge=0.0)
    draught_fraction_female: float = Field(default=0.0, ge=0.0, le=1.0)
    draught_fraction_male: float = Field(default=0.0, ge=0.0, le=1.0)
    ch4_mitigation_factor: float = Field(default=1.0, ge=0.0)
    carcass_dressing_fraction: float = Field(default=0.5, ge=0.0, le=1.0)
    bone_free_meat_fraction: float = Field(default=0.75, ge=0.0, le=1.0)
    meat_protein_fraction: float = Field(default=0.2, ge=0.0, le=1.0)


class LivestockEnterprise(BaseModel):
    enterprise_id: str
    rations: list[RationProfileRecord]
    manure_systems: list[ManureManagementRecord]
    cohorts: list[LivestockCohortRecord]

    @model_validator(mode="after")
    def validate_livestock_links(self) -> LivestockEnterprise:
        ration_ids = [item.ration_id for item in self.rations]
        if len(set(ration_ids)) != len(ration_ids):
            raise ValueError("ration_id values must be unique within an enterprise")
        cohort_ids = [item.cohort_id for item in self.cohorts]
        if len(set(cohort_ids)) != len(cohort_ids):
            raise ValueError("cohort_id values must be unique within an enterprise")
        missing_rations = sorted(
            {item.ration_id for item in self.cohorts}.difference(ration_ids)
        )
        if missing_rations:
            raise ValueError(f"Cohorts reference unknown rations: {missing_rations}")
        if not self.manure_systems:
            raise ValueError("At least one manure management system is required")
        manure_total = sum(item.fraction for item in self.manure_systems)
        if abs(manure_total - 1.0) > 1e-9:
            raise ValueError("Manure management fractions must sum to one")
        return self


class FarmEnergyRecord(BaseModel):
    source_name: str
    amount: float = Field(ge=0.0)
    unit: str
    emission_factor_kg_co2e_per_unit: float | None = Field(default=None, ge=0.0)


class FarmSurvey(BaseModel):
    farm_id: str
    country: Literal["Ethiopia", "Kenya"]
    basin: Literal["Omo Ghibe River Basin", "Lake Victoria Basin"]
    survey_date: date
    land_units: list[LandUnit]
    soil_profiles: list[SoilProfile] = Field(default_factory=list)
    livestock_enterprises: list[LivestockEnterprise] = Field(default_factory=list)
    energy_records: list[FarmEnergyRecord] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_references(self) -> FarmSurvey:
        unit_ids = {unit.land_unit_id for unit in self.land_units}
        if len(unit_ids) != len(self.land_units):
            raise ValueError("land_unit_id values must be unique within a farm")
        enterprise_ids = [item.enterprise_id for item in self.livestock_enterprises]
        if len(set(enterprise_ids)) != len(enterprise_ids):
            raise ValueError("enterprise_id values must be unique within a farm")
        for profile in self.soil_profiles:
            if profile.farm_id != self.farm_id:
                raise ValueError("Soil profile farm_id does not match the farm survey")
            if profile.land_unit_id not in unit_ids:
                raise ValueError("Soil profile references an unknown land unit")
        return self

    @property
    def total_area_ha(self) -> float:
        return sum(unit.area_ha for unit in self.land_units)