"""Measured soil observation adapters for stock and repeated profile calculations."""

from __future__ import annotations

from collections.abc import Mapping

from .input_schema import SoilProfile
from .soc_stock import (
    SoilLayer,
    aggregate_soc_layers_t_c_ha,
    equivalent_soil_mass_change_t_c_ha,
)


def soil_profile_to_layers(
    profile: SoilProfile,
    bulk_density_overrides: Mapping[int, float] | None = None,
) -> tuple[SoilLayer, ...]:
    """Convert a validated profile to calculation layers.

    Missing bulk density is never treated as zero. A measured value or an
    explicitly supplied locally validated replacement is required for every
    layer used in stock calculations.
    """

    overrides = dict(bulk_density_overrides or {})
    layers: list[SoilLayer] = []
    ordered = sorted(profile.layers, key=lambda layer: layer.depth_top_cm)
    for index, layer in enumerate(ordered):
        bulk_density = layer.bulk_density_g_cm3
        if bulk_density is None:
            bulk_density = overrides.get(index)
        if bulk_density is None:
            raise ValueError(
                f"Bulk density is required for profile {profile.profile_id} layer {index}"
            )
        layers.append(
            SoilLayer(
                soc_g_kg=layer.soc_g_kg,
                bulk_density_g_cm3=float(bulk_density),
                depth_top_cm=layer.depth_top_cm,
                depth_bottom_cm=layer.depth_bottom_cm,
                coarse_fragment_percent=layer.coarse_fragment_percent,
            )
        )
    return tuple(layers)


def quantified_profile_soc_t_c_ha(
    profile: SoilProfile,
    target_depth_cm: float = 30.0,
    bulk_density_overrides: Mapping[int, float] | None = None,
) -> float:
    if profile.purpose != "quantification":
        raise ValueError("Only quantification profiles can produce a quantified SOC stock")
    layers = soil_profile_to_layers(profile, bulk_density_overrides)
    return aggregate_soc_layers_t_c_ha(layers, target_depth_cm)


def repeated_profile_esm_change_t_c_ha(
    baseline: SoilProfile,
    intervention: SoilProfile,
    reference_depth_cm: float = 30.0,
    baseline_bulk_density_overrides: Mapping[int, float] | None = None,
    intervention_bulk_density_overrides: Mapping[int, float] | None = None,
) -> float:
    if baseline.land_unit_id != intervention.land_unit_id:
        raise ValueError("Repeated SOC profiles must refer to the same land unit")
    baseline_layers = soil_profile_to_layers(
        baseline,
        baseline_bulk_density_overrides,
    )
    intervention_layers = soil_profile_to_layers(
        intervention,
        intervention_bulk_density_overrides,
    )
    return equivalent_soil_mass_change_t_c_ha(
        baseline_layers,
        intervention_layers,
        reference_depth_cm,
    )
