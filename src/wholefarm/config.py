"""Configuration models for the whole farm model."""

from __future__ import annotations

from pydantic import BaseModel, Field


class GeographyConfig(BaseModel):
    countries: tuple[str, ...] = ("Ethiopia", "Kenya")
    basins: tuple[str, ...] = ("Omo Ghibe River Basin", "Lake Victoria Basin")


class MethodologyConfig(BaseModel):
    vm0042_version: str = "2.2"
    vmd0053_version: str = "2.1"
    vt0014_version: str = "1.0"
    gleam_repository: str = "un-fao/GLEAM"
    gleam_commit: str = "90e416197e89093c4f3a347b263ba805d33d4aac"
    florida_soc_repository: str = "Ecosystem-Services-GeoAI/florida-grazing-soc-qrf"
    florida_soc_commit: str = "48c3794256d88e87e3cc83bb66694a5f11bbbce0"
    rothc_repository: str = "Rothamsted-Models/RothC_Py"
    rothc_commit: str = "bd90ce3cf616d5316042b73a3b1f09c5b6e3b361"


class Constants(BaseModel):
    carbon_to_co2: float = 44.0 / 12.0
    gwp_ch4: float = 27.2
    gwp_n2o: float = 273.0
    methane_energy_mj_per_kg: float = 55.65
    methane_density_kg_per_m3: float = 0.67


class ProjectConfig(BaseModel):
    name: str = "Whole Farm GHG and SOC Model"
    start_year: int = 2026
    end_year: int = 2030
    soc_depth_cm: float = Field(default=30.0, ge=30.0)
    status: str = "RESEARCH"


class ModelConfig(BaseModel):
    project: ProjectConfig = ProjectConfig()
    geography: GeographyConfig = GeographyConfig()
    methodology: MethodologyConfig = MethodologyConfig()
    constants: Constants = Constants()
