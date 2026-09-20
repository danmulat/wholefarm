"""Measured soil organic carbon stock calculations with VM0042 depth checks."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

VM0042_MINIMUM_SOC_DEPTH_CM = 30.0


@dataclass(frozen=True)
class SoilLayer:
    soc_g_kg: float
    bulk_density_g_cm3: float
    depth_top_cm: float
    depth_bottom_cm: float
    coarse_fragment_percent: float = 0.0

    @property
    def fine_soil_mass_t_ha(self) -> float:
        return fine_soil_mass_t_ha(
            self.bulk_density_g_cm3,
            self.depth_top_cm,
            self.depth_bottom_cm,
            self.coarse_fragment_percent,
        )

    @property
    def stock_t_c_ha(self) -> float:
        return soc_stock_t_c_ha(
            self.soc_g_kg,
            self.bulk_density_g_cm3,
            self.depth_top_cm,
            self.depth_bottom_cm,
            self.coarse_fragment_percent,
        )


def soc_stock_t_c_ha(
    soc_g_kg: float,
    bulk_density_g_cm3: float,
    depth_top_cm: float,
    depth_bottom_cm: float,
    coarse_fragment_percent: float = 0.0,
) -> float:
    if soc_g_kg < 0:
        raise ValueError("SOC concentration cannot be negative")
    if bulk_density_g_cm3 <= 0:
        raise ValueError("Bulk density must be positive")
    if depth_top_cm < 0:
        raise ValueError("Depth top cannot be negative")
    if depth_bottom_cm <= depth_top_cm:
        raise ValueError("Depth bottom must be greater than depth top")
    if not 0 <= coarse_fragment_percent < 100:
        raise ValueError("Coarse fragment percent must be between zero and one hundred")
    thickness_cm = depth_bottom_cm - depth_top_cm
    fine_fraction = 1.0 - coarse_fragment_percent / 100.0
    return soc_g_kg * bulk_density_g_cm3 * thickness_cm * 0.1 * fine_fraction


def validate_vm0042_depth(
    depth_bottom_cm: float,
    purpose: Literal["quantification", "calibration_validation"] = "quantification",
    extrapolation_method: str | None = None,
) -> None:
    if depth_bottom_cm >= VM0042_MINIMUM_SOC_DEPTH_CM:
        return
    if purpose == "calibration_validation" and extrapolation_method:
        return
    if purpose == "calibration_validation":
        raise ValueError(
            "Shallower calibration or validation data require a documented extrapolation method"
        )
    raise ValueError("VM0042 SOC quantification requires soil data to at least 30 cm depth")


def aggregate_soc_layers_t_c_ha(
    layers: Iterable[SoilLayer],
    target_depth_cm: float = VM0042_MINIMUM_SOC_DEPTH_CM,
) -> float:
    if target_depth_cm < VM0042_MINIMUM_SOC_DEPTH_CM:
        raise ValueError("VM0042 target SOC depth must be at least 30 cm")
    ordered = sorted(layers, key=lambda item: (item.depth_top_cm, item.depth_bottom_cm))
    if not ordered:
        raise ValueError("At least one soil layer is required")

    expected_top = 0.0
    for layer in ordered:
        if layer.depth_top_cm > expected_top + 1e-9:
            raise ValueError("Soil layers contain a gap before the target depth")
        if layer.depth_top_cm < expected_top - 1e-9:
            raise ValueError("Soil layers overlap")
        expected_top = layer.depth_bottom_cm
        if expected_top >= target_depth_cm:
            break
    if expected_top < target_depth_cm:
        raise ValueError("Soil layers do not reach the VM0042 target depth")

    total = 0.0
    for layer in ordered:
        if layer.depth_top_cm >= target_depth_cm:
            continue
        bottom = min(layer.depth_bottom_cm, target_depth_cm)
        total += soc_stock_t_c_ha(
            layer.soc_g_kg,
            layer.bulk_density_g_cm3,
            layer.depth_top_cm,
            bottom,
            layer.coarse_fragment_percent,
        )
    return total


def reference_soil_mass_t_ha(
    layers: Iterable[SoilLayer],
    target_depth_cm: float = VM0042_MINIMUM_SOC_DEPTH_CM,
) -> float:
    """Return fine soil mass to the requested physical reference depth."""

    if target_depth_cm <= 0:
        raise ValueError("target_depth_cm must be positive")
    ordered = sorted(layers, key=lambda item: (item.depth_top_cm, item.depth_bottom_cm))
    if not ordered:
        raise ValueError("At least one soil layer is required")

    expected_top = 0.0
    total_mass = 0.0
    for layer in ordered:
        if layer.depth_top_cm > expected_top + 1e-9:
            raise ValueError("Soil layers contain a gap before the reference depth")
        if layer.depth_top_cm < expected_top - 1e-9:
            raise ValueError("Soil layers overlap")
        if layer.depth_top_cm >= target_depth_cm:
            break

        bottom = min(layer.depth_bottom_cm, target_depth_cm)
        total_mass += fine_soil_mass_t_ha(
            layer.bulk_density_g_cm3,
            layer.depth_top_cm,
            bottom,
            layer.coarse_fragment_percent,
        )
        expected_top = layer.depth_bottom_cm
        if bottom >= target_depth_cm:
            return total_mass

    raise ValueError("Soil layers do not reach the requested reference depth")


def equivalent_soil_mass_soc_t_c_ha(
    layers: Iterable[SoilLayer],
    target_fine_soil_mass_t_ha: float,
) -> float:
    """Calculate SOC stock for a fixed fine earth soil mass.

    The function accumulates whole layers and, when needed, a proportional
    fraction of the last layer. SOC concentration is assumed uniform within
    each supplied layer.
    """

    if target_fine_soil_mass_t_ha <= 0:
        raise ValueError("target_fine_soil_mass_t_ha must be positive")
    ordered = sorted(layers, key=lambda item: (item.depth_top_cm, item.depth_bottom_cm))
    if not ordered:
        raise ValueError("At least one soil layer is required")

    expected_top = 0.0
    remaining_mass = target_fine_soil_mass_t_ha
    total_soc = 0.0

    for layer in ordered:
        if layer.depth_top_cm > expected_top + 1e-9:
            raise ValueError("Soil layers contain a gap")
        if layer.depth_top_cm < expected_top - 1e-9:
            raise ValueError("Soil layers overlap")
        expected_top = layer.depth_bottom_cm

        layer_mass = layer.fine_soil_mass_t_ha
        if layer_mass <= 0:
            continue
        used_mass = min(layer_mass, remaining_mass)
        total_soc += used_mass * layer.soc_g_kg / 1000.0
        remaining_mass -= used_mass
        if remaining_mass <= 1e-9:
            return total_soc

    raise ValueError("Soil profile does not contain enough fine earth mass")


def equivalent_soil_mass_change_t_c_ha(
    baseline_layers: Iterable[SoilLayer],
    intervention_layers: Iterable[SoilLayer],
    reference_depth_cm: float = VM0042_MINIMUM_SOC_DEPTH_CM,
) -> float:
    """Compare two profiles using the baseline fine soil mass as the reference."""

    baseline_tuple = tuple(baseline_layers)
    intervention_tuple = tuple(intervention_layers)
    reference_mass = reference_soil_mass_t_ha(
        baseline_tuple,
        reference_depth_cm,
    )
    baseline_stock = equivalent_soil_mass_soc_t_c_ha(
        baseline_tuple,
        reference_mass,
    )
    intervention_stock = equivalent_soil_mass_soc_t_c_ha(
        intervention_tuple,
        reference_mass,
    )
    return intervention_stock - baseline_stock