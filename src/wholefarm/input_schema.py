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
    def validate_depth_interval(self) -> "SoilLayerObservation":
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
    def validate_profile_depth(self) -> "SoilProfile":
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


class FarmSurvey(BaseModel):
    farm_id: str
    country: Literal["Ethiopia", "Kenya"]
    basin: Literal["Omo Ghibe River Basin", "Lake Victoria Basin"]
    survey_date: date
    land_units: list[LandUnit]
    soil_profiles: list[SoilProfile] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_references(self) -> "FarmSurvey":
        unit_ids = {unit.land_unit_id for unit in self.land_units}
        if len(unit_ids) != len(self.land_units):
            raise ValueError("land_unit_id values must be unique within a farm")
        for profile in self.soil_profiles:
            if profile.farm_id != self.farm_id:
                raise ValueError("Soil profile farm_id does not match the farm survey")
            if profile.land_unit_id not in unit_ids:
                raise ValueError("Soil profile references an unknown land unit")
        return self

    @property
    def total_area_ha(self) -> float:
        return sum(unit.area_ha for unit in self.land_units)
