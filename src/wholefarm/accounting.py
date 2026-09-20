"""Whole farm baseline and intervention accounting."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LivestockGHG:
    enteric_ch4_co2e_t: float = 0.0
    manure_ch4_co2e_t: float = 0.0
    manure_n2o_co2e_t: float = 0.0
    feed_production_co2e_t: float = 0.0

    @property
    def total_co2e_t(self) -> float:
        return (
            self.enteric_ch4_co2e_t
            + self.manure_ch4_co2e_t
            + self.manure_n2o_co2e_t
            + self.feed_production_co2e_t
        )


@dataclass(frozen=True)
class FarmGHGInventory:
    livestock: LivestockGHG = field(default_factory=LivestockGHG)
    soil_n2o_co2e_t: float = 0.0
    crop_inputs_co2e_t: float = 0.0
    energy_co2e_t: float = 0.0
    purchased_inputs_co2e_t: float = 0.0
    other_co2e_t: float = 0.0

    @property
    def gross_co2e_t(self) -> float:
        return (
            self.livestock.total_co2e_t
            + self.soil_n2o_co2e_t
            + self.crop_inputs_co2e_t
            + self.energy_co2e_t
            + self.purchased_inputs_co2e_t
            + self.other_co2e_t
        )


@dataclass(frozen=True)
class CarbonStockChange:
    soil_co2e_t: float = 0.0
    tree_biomass_co2e_t: float = 0.0

    @property
    def total_removals_co2e_t(self) -> float:
        return self.soil_co2e_t + self.tree_biomass_co2e_t


@dataclass(frozen=True)
class FarmScenarioResult:
    scenario_name: str
    emissions: FarmGHGInventory
    removals: CarbonStockChange = field(default_factory=CarbonStockChange)
    production: dict[str, float] = field(default_factory=dict)

    @property
    def net_co2e_t(self) -> float:
        return self.emissions.gross_co2e_t - self.removals.total_removals_co2e_t


@dataclass(frozen=True)
class ScenarioComparison:
    baseline: FarmScenarioResult
    intervention: FarmScenarioResult

    @property
    def gross_emission_reduction_co2e_t(self) -> float:
        return self.baseline.emissions.gross_co2e_t - self.intervention.emissions.gross_co2e_t

    @property
    def additional_removals_co2e_t(self) -> float:
        return (
            self.intervention.removals.total_removals_co2e_t
            - self.baseline.removals.total_removals_co2e_t
        )

    @property
    def total_climate_benefit_co2e_t(self) -> float:
        return self.baseline.net_co2e_t - self.intervention.net_co2e_t
