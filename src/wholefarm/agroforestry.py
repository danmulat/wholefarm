"""Tree biomass carbon accounting kept separate from soil organic carbon."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TreeBiomassStock:
    aboveground_dry_matter_t: float
    belowground_dry_matter_t: float
    carbon_fraction: float

    def __post_init__(self) -> None:
        if self.aboveground_dry_matter_t < 0 or self.belowground_dry_matter_t < 0:
            raise ValueError("Tree dry matter stocks must be nonnegative")
        if not 0.0 < self.carbon_fraction <= 1.0:
            raise ValueError("carbon_fraction must be greater than zero and at most one")

    @property
    def total_dry_matter_t(self) -> float:
        return self.aboveground_dry_matter_t + self.belowground_dry_matter_t

    @property
    def carbon_t(self) -> float:
        return self.total_dry_matter_t * self.carbon_fraction

    @property
    def co2e_t(self) -> float:
        return self.carbon_t * 44.0 / 12.0


@dataclass(frozen=True)
class TreeCarbonChange:
    initial_carbon_t: float
    final_carbon_t: float

    @property
    def change_t_c(self) -> float:
        return self.final_carbon_t - self.initial_carbon_t

    @property
    def change_co2e_t(self) -> float:
        return self.change_t_c * 44.0 / 12.0


def calculate_tree_carbon_change(
    initial: TreeBiomassStock,
    final: TreeBiomassStock,
) -> TreeCarbonChange:
    return TreeCarbonChange(initial.carbon_t, final.carbon_t)
