"""Block based digital SOC prediction following the Florida reference workflow.

The raster writer uses the same core mapping pattern as the pinned Florida
repository: read feature rasters by block, mask invalid pixels, predict a mean
SOC surface with Random Forest, predict Q05 and Q95 with Quantile Regression
Forest, and write three output bands. Soil depth is governed by the whole farm
VM0042 configuration and is not inherited from the Florida study.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .soc_qrf import QRFModelBundle


@dataclass(frozen=True)
class SOCBlockPrediction:
    mean: np.ndarray
    q05: np.ndarray
    q50: np.ndarray
    q95: np.ndarray
    interval_width_90: np.ndarray
    valid_mask: np.ndarray


@dataclass(frozen=True)
class SOCAreaSummary:
    n_valid: int
    total_weight: float
    mean_soc_t_c_ha: float
    q05_surface_mean_t_c_ha: float
    q50_surface_mean_t_c_ha: float
    q95_surface_mean_t_c_ha: float
    mean_interval_width_90_t_c_ha: float


def predict_soc_table(
    bundle: QRFModelBundle,
    features: pd.DataFrame,
) -> pd.DataFrame:
    """Predict mean SOC and Q05, Q50, Q95 for a feature table."""

    mean = bundle.predict_mean(features)
    quantiles = bundle.predict_quantiles(features, (0.05, 0.50, 0.95))
    result = pd.concat([mean, quantiles], axis=1)
    result["interval_width_90"] = result["q95"] - result["q05"]
    return result


def _invalid_pixel_mask(
    feature_stack: np.ndarray,
    nodata_value: float | None,
) -> np.ndarray:
    if feature_stack.ndim != 3:
        raise ValueError("feature_stack must have shape bands by rows by columns")
    invalid = np.any(~np.isfinite(feature_stack), axis=0)
    if nodata_value is not None:
        invalid = invalid | np.any(feature_stack == nodata_value, axis=0)
    return invalid


def predict_soc_block(
    bundle: QRFModelBundle,
    feature_stack: np.ndarray,
    feature_names: Sequence[str],
    nodata_value: float | None = None,
    output_nodata: float = -9999.0,
) -> SOCBlockPrediction:
    """Predict one raster block while preserving the reference band ordering."""

    array = np.asarray(feature_stack, dtype=np.float32)
    if array.ndim != 3:
        raise ValueError("feature_stack must have three dimensions")
    bands, rows, columns = array.shape
    if bands != len(feature_names):
        raise ValueError("feature_names length must equal the raster band count")

    selected = tuple(bundle.selected_features)
    names = tuple(feature_names)
    if names != selected:
        raise ValueError(
            "Raster feature band order must exactly match the selected model feature order"
        )

    invalid = _invalid_pixel_mask(array, nodata_value)
    valid = ~invalid
    flat_valid = valid.reshape(-1)

    mean_flat = np.full(rows * columns, output_nodata, dtype=np.float32)
    q05_flat = np.full(rows * columns, output_nodata, dtype=np.float32)
    q50_flat = np.full(rows * columns, output_nodata, dtype=np.float32)
    q95_flat = np.full(rows * columns, output_nodata, dtype=np.float32)

    if np.any(flat_valid):
        matrix = array.reshape(bands, -1).T
        frame = pd.DataFrame(
            matrix[flat_valid],
            columns=list(feature_names),
        )
        predicted = predict_soc_table(bundle, frame)
        mean_flat[flat_valid] = predicted["predicted_mean"].to_numpy(dtype=np.float32)
        q05_flat[flat_valid] = predicted["q05"].to_numpy(dtype=np.float32)
        q50_flat[flat_valid] = predicted["q50"].to_numpy(dtype=np.float32)
        q95_flat[flat_valid] = predicted["q95"].to_numpy(dtype=np.float32)

    mean = mean_flat.reshape(rows, columns)
    q05 = q05_flat.reshape(rows, columns)
    q50 = q50_flat.reshape(rows, columns)
    q95 = q95_flat.reshape(rows, columns)
    interval = np.full((rows, columns), output_nodata, dtype=np.float32)
    interval[valid] = q95[valid] - q05[valid]

    return SOCBlockPrediction(
        mean=mean,
        q05=q05,
        q50=q50,
        q95=q95,
        interval_width_90=interval,
        valid_mask=valid,
    )


def summarize_soc_predictions(
    predictions: pd.DataFrame,
    weights: Sequence[float] | None = None,
) -> SOCAreaSummary:
    """Return area weighted summaries of pixel prediction surfaces.

    The weighted Q05 and Q95 surface means are descriptive summaries. They are
    not treated as a probabilistic farm or basin confidence interval because
    spatial correlation must be propagated separately.
    """

    required = {"predicted_mean", "q05", "q50", "q95", "interval_width_90"}
    missing = required.difference(predictions.columns)
    if missing:
        raise ValueError(f"Missing prediction columns: {sorted(missing)}")

    values = predictions.loc[:, sorted(required)].replace([np.inf, -np.inf], np.nan)
    valid = values.notna().all(axis=1).to_numpy()
    if not np.any(valid):
        raise ValueError("At least one valid prediction row is required")

    if weights is None:
        weight_array = np.ones(len(predictions), dtype=float)
    else:
        weight_array = np.asarray(weights, dtype=float)
        if len(weight_array) != len(predictions):
            raise ValueError("weights length must equal prediction row count")
        if np.any(~np.isfinite(weight_array)) or np.any(weight_array < 0):
            raise ValueError("weights must be finite and nonnegative")

    valid_weights = weight_array[valid]
    if valid_weights.sum() <= 0:
        raise ValueError("Valid prediction weights must sum to a positive value")

    subset = predictions.loc[valid]

    def weighted(column: str) -> float:
        return float(np.average(subset[column].to_numpy(dtype=float), weights=valid_weights))

    return SOCAreaSummary(
        n_valid=int(valid.sum()),
        total_weight=float(valid_weights.sum()),
        mean_soc_t_c_ha=weighted("predicted_mean"),
        q05_surface_mean_t_c_ha=weighted("q05"),
        q50_surface_mean_t_c_ha=weighted("q50"),
        q95_surface_mean_t_c_ha=weighted("q95"),
        mean_interval_width_90_t_c_ha=weighted("interval_width_90"),
    )


def write_soc_prediction_raster(
    bundle: QRFModelBundle,
    input_feature_tif: str | Path,
    output_tif: str | Path,
    feature_names: Sequence[str],
    output_nodata: float = -9999.0,
) -> Path:
    """Write mean, Q05 and Q95 SOC bands block by block.

    Rasterio is optional and is only required when this raster function is used.
    """

    try:
        import rasterio
    except ImportError as exc:
        raise ImportError(
            "Raster SOC mapping requires the optional geo dependencies"
        ) from exc

    input_path = Path(input_feature_tif)
    output_path = Path(output_tif)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(input_path) as source:
        if source.count != len(feature_names):
            raise ValueError("Input raster band count must equal feature_names length")
        if tuple(feature_names) != tuple(bundle.selected_features):
            raise ValueError(
                "Input raster band order must exactly match selected model features"
            )

        profile = source.profile.copy()
        profile.update(dtype="float32", count=3, nodata=output_nodata)

        with rasterio.open(output_path, "w", **profile) as destination:
            destination.set_band_description(1, "soc_mean_t_c_ha")
            destination.set_band_description(2, "soc_q05_t_c_ha")
            destination.set_band_description(3, "soc_q95_t_c_ha")

            for _, window in source.block_windows(1):
                block = source.read(window=window).astype(np.float32)
                prediction = predict_soc_block(
                    bundle,
                    block,
                    feature_names,
                    nodata_value=source.nodata,
                    output_nodata=output_nodata,
                )
                destination.write(prediction.mean, 1, window=window)
                destination.write(prediction.q05, 2, window=window)
                destination.write(prediction.q95, 3, window=window)

    return output_path