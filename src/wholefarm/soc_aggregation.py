"""Area weighted aggregation of digital SOC prediction surfaces."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SpatialSOCSummary:
    area_ha: float
    mean_soc_t_c_ha: float
    median_surface_soc_t_c_ha: float
    q05_surface_soc_t_c_ha: float
    q95_surface_soc_t_c_ha: float
    mean_soc_total_t_c: float

    @property
    def mean_soc_total_t_co2e(self) -> float:
        return self.mean_soc_total_t_c * 44.0 / 12.0


def aggregate_soc_pixels(
    predictions: pd.DataFrame,
    pixel_area_ha: Sequence[float],
) -> SpatialSOCSummary:
    required = {"predicted_mean", "q05", "q50", "q95"}
    missing = required.difference(predictions.columns)
    if missing:
        raise ValueError(f"Missing SOC prediction columns: {sorted(missing)}")

    areas = np.asarray(pixel_area_ha, dtype=float)
    if len(areas) != len(predictions):
        raise ValueError("pixel_area_ha length must match prediction row count")
    if np.any(~np.isfinite(areas)) or np.any(areas < 0):
        raise ValueError("Pixel areas must be finite and nonnegative")

    frame = predictions.loc[:, sorted(required)].replace([np.inf, -np.inf], np.nan)
    valid = frame.notna().all(axis=1).to_numpy() & (areas > 0)
    if not np.any(valid):
        raise ValueError("At least one valid positive area SOC pixel is required")

    valid_areas = areas[valid]
    subset = predictions.loc[valid]
    total_area = float(valid_areas.sum())

    def weighted(column: str) -> float:
        return float(
            np.average(
                subset[column].to_numpy(dtype=float),
                weights=valid_areas,
            )
        )

    mean_stock = weighted("predicted_mean")
    return SpatialSOCSummary(
        area_ha=total_area,
        mean_soc_t_c_ha=mean_stock,
        median_surface_soc_t_c_ha=weighted("q50"),
        q05_surface_soc_t_c_ha=weighted("q05"),
        q95_surface_soc_t_c_ha=weighted("q95"),
        mean_soc_total_t_c=mean_stock * total_area,
    )


def aggregate_soc_by_group(
    predictions: pd.DataFrame,
    pixel_area_ha: Sequence[float],
    group_ids: Sequence[str],
) -> pd.DataFrame:
    areas = np.asarray(pixel_area_ha, dtype=float)
    groups = np.asarray(group_ids, dtype=object)
    if len(predictions) != len(areas) or len(areas) != len(groups):
        raise ValueError("Predictions, areas and group ids must have equal row counts")

    rows: list[dict[str, float | str]] = []
    for group in pd.unique(groups):
        mask = groups == group
        summary = aggregate_soc_pixels(
            predictions.loc[mask].reset_index(drop=True),
            areas[mask],
        )
        rows.append(
            {
                "group_id": str(group),
                "area_ha": summary.area_ha,
                "mean_soc_t_c_ha": summary.mean_soc_t_c_ha,
                "q05_surface_soc_t_c_ha": summary.q05_surface_soc_t_c_ha,
                "q50_surface_soc_t_c_ha": summary.median_surface_soc_t_c_ha,
                "q95_surface_soc_t_c_ha": summary.q95_surface_soc_t_c_ha,
                "mean_soc_total_t_c": summary.mean_soc_total_t_c,
                "mean_soc_total_t_co2e": summary.mean_soc_total_t_co2e,
            }
        )
    return pd.DataFrame(rows)
