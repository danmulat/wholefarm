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