"""Physical manure nitrogen and carbon bookkeeping for the whole farm model.

The module connects GLEAM excretion outputs to crop and RothC inputs without
embedding default recovery efficiencies. Every loss and recovery fraction is
provided explicitly by the scenario.
"""

from __future__ import annotations

from dataclasses import dataclass


def _fraction(value: float, name: str) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between zero and one")


@dataclass(frozen=True)
class ManureRecoveryConfig:
    collection_fraction: float
    storage_n_retention_fraction: float
    field_application_fraction: float
    volatile_solids_recovery_fraction: float
    carbon_fraction_of_recovered_vs: float

    def __post_init__(self) -> None:
        for value, name in (
            (self.collection_fraction, "collection_fraction"),
            (self.storage_n_retention_fraction, "storage_n_retention_fraction"),
            (self.field_application_fraction, "field_application_fraction"),
            (
                self.volatile_solids_recovery_fraction,
                "volatile_solids_recovery_fraction",
            ),
            (
                self.carbon_fraction_of_recovered_vs,
                "carbon_fraction_of_recovered_vs",
            ),
        ):
            _fraction(value, name)


@dataclass(frozen=True)
class ManureNutrientFlow:
    excreted_n_kg: float
    collected_n_kg: float
    retained_after_storage_n_kg: float
    field_applied_n_kg: float
    excreted_vs_kg: float
    recovered_vs_kg: float
    field_applied_c_kg: float

    def field_applied_c_t_ha(self, receiving_area_ha: float) -> float:
        if receiving_area_ha <= 0:
            raise ValueError("receiving_area_ha must be positive")
        return self.field_applied_c_kg / 1000.0 / receiving_area_ha

    def field_applied_n_kg_ha(self, receiving_area_ha: float) -> float:
        if receiving_area_ha <= 0:
            raise ValueError("receiving_area_ha must be positive")
        return self.field_applied_n_kg / receiving_area_ha


def route_manure_to_fields(
    excreted_n_kg: float,
    excreted_vs_kg: float,
    config: ManureRecoveryConfig,
) -> ManureNutrientFlow:
    if excreted_n_kg < 0 or excreted_vs_kg < 0:
        raise ValueError("Excreted nitrogen and volatile solids must be nonnegative")

    collected_n = excreted_n_kg * config.collection_fraction
    retained_n = collected_n * config.storage_n_retention_fraction
    field_n = retained_n * config.field_application_fraction

    collected_vs = excreted_vs_kg * config.collection_fraction
    recovered_vs = collected_vs * config.volatile_solids_recovery_fraction
    field_vs = recovered_vs * config.field_application_fraction
    field_c = field_vs * config.carbon_fraction_of_recovered_vs

    return ManureNutrientFlow(
        excreted_n_kg=excreted_n_kg,
        collected_n_kg=collected_n,
        retained_after_storage_n_kg=retained_n,
        field_applied_n_kg=field_n,
        excreted_vs_kg=excreted_vs_kg,
        recovered_vs_kg=recovered_vs,
        field_applied_c_kg=field_c,
    )
