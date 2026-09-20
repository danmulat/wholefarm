"""Digital SOC Quantile Regression Forest workflow.

The model structure follows the public Florida grazing SOC Python workflow.
Environmental data sources and spatial validation settings must be calibrated
for Ethiopia and Kenya.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import pi
from typing import Iterable, Sequence

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.outliers_influence import variance_inflation_factor

DEFAULT_QUANTILES = tuple(range(5, 100, 5))


@dataclass(frozen=True)
class QRFWorkflowConfig:
    outer_cv: int = 5
    inner_cv: int = 3
    correlation_distance_threshold: float = 0.2
    vif_threshold: float = 10.0
    minimum_soc_depth_cm: float = 30.0
    random_state: int = 42
    quantiles: tuple[int, ...] = DEFAULT_QUANTILES

    def __post_init__(self) -> None:
        if self.minimum_soc_depth_cm < 30.0:
            raise ValueError("VM0042 SOC quantification depth must be at least 30 cm")


def _array(values: Iterable[float]) -> np.ndarray:
    return np.asarray(tuple(values), dtype=float).ravel()


def _trend(values: np.ndarray) -> float:
    x = np.arange(values.size, dtype=float)
    mask = np.isfinite(values)
    if mask.sum() < 2:
        return float("nan")
    return float(np.polyfit(x[mask], values[mask], 1)[0])


def _autocorr(values: np.ndarray, lag: int) -> float:
    if values.size <= lag:
        return float("nan")
    x = values[:-lag]
    y = values[lag:]
    mask = np.isfinite(x) & np.isfinite(y)
    if mask.sum() < 2:
        return float("nan")
    x = x[mask]
    y = y[mask]
    if np.std(x) == 0 or np.std(y) == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def _fourier(values: np.ndarray, harmonic: int, months_in_year: int = 12) -> tuple[float, float]:
    t = np.arange(values.size, dtype=float)
    mask = np.isfinite(values)
    if mask.sum() < 3:
        return float("nan"), float("nan")
    omega = 2.0 * pi * harmonic / months_in_year
    design = np.column_stack([np.cos(omega * t[mask]), np.sin(omega * t[mask])])
    coefficients, _, _, _ = np.linalg.lstsq(design, values[mask], rcond=None)
    amplitude = float(np.sqrt(coefficients[0] ** 2 + coefficients[1] ** 2))
    phase = float(np.arctan2(coefficients[1], coefficients[0]))
    return amplitude, phase


def compute_common_ts_features(
    values: Iterable[float],
    months_in_year: int = 12,
) -> dict[str, float]:
    x = _array(values)
    finite = x[np.isfinite(x)]
    if finite.size == 0:
        raise ValueError("At least one finite time series observation is required")
    mean = float(np.nanmean(x))
    std = float(np.nanstd(x, ddof=1)) if finite.size > 1 else float("nan")
    q20 = float(np.nanpercentile(x, 20))
    q80 = float(np.nanpercentile(x, 80))
    count = int(np.isfinite(x).sum())

    seasonality = float("nan")
    interannual_std = float("nan")
    interannual_cv = float("nan")
    if x.size >= months_in_year and x.size % months_in_year == 0:
        matrix = x.reshape(x.size // months_in_year, months_in_year)
        monthly_means = np.nanmean(matrix, axis=0)
        if mean != 0:
            seasonality = float((np.nanmax(monthly_means) - np.nanmin(monthly_means)) / mean)
        yearly_means = np.nanmean(matrix, axis=1)
        if yearly_means.size > 1:
            interannual_std = float(np.nanstd(yearly_means, ddof=1))
            interannual_cv = interannual_std / float(np.nanmean(yearly_means))

    amp1, phase1 = _fourier(x, 1, months_in_year)
    amp2, phase2 = _fourier(x, 2, months_in_year)

    return {
        "mean": mean,
        "std": std,
        "cv": std / mean if np.isfinite(std) and mean != 0 else float("nan"),
        "min": float(np.nanmin(x)),
        "max": float(np.nanmax(x)),
        "range": float(np.nanmax(x) - np.nanmin(x)),
        "trend_slope_per_month": _trend(x),
        "autocorr_lag1": _autocorr(x, 1),
        "autocorr_lag12": _autocorr(x, 12),
        "q20": q20,
        "q80": q80,
        "frac_below_q20": float(np.sum(x < q20) / count),
        "frac_above_q80": float(np.sum(x > q80) / count),
        "integral_sum": float(np.nansum(x)),
        "sma_anomaly_sum": float(np.nansum(x - mean)),
        "seasonality_index": seasonality,
        "interannual_std": interannual_std,
        "interannual_cv": interannual_cv,
        "fourier1_amplitude": amp1,
        "fourier1_phase_rad": phase1,
        "fourier2_amplitude": amp2,
        "fourier2_phase_rad": phase2,
    }


def correlation_cluster_select(
    features: pd.DataFrame,
    distance_threshold: float = 0.2,
) -> tuple[list[str], pd.DataFrame]:
    numeric = features.select_dtypes(include=[np.number]).copy()
    numeric = numeric.loc[:, numeric.nunique(dropna=True) > 1]
    numeric = numeric.T.drop_duplicates().T
    if numeric.shape[1] <= 1:
        columns = list(numeric.columns)
        return columns, pd.DataFrame({"variable": columns, "cluster": [1] * len(columns)})
    correlation = numeric.corr().clip(-1.0, 1.0).fillna(0.0)
    distance = 1.0 - np.abs(correlation.to_numpy())
    np.fill_diagonal(distance, 0.0)
    linked = linkage(squareform(distance, checks=True), method="average")
    clusters = fcluster(linked, t=distance_threshold, criterion="distance")
    assignment = pd.DataFrame({"variable": numeric.columns, "cluster": clusters})
    selected = []
    for _, group in assignment.groupby("cluster", sort=True):
        columns = group["variable"].tolist()
        missing = numeric[columns].isna().mean()
        selected.append(str(missing.sort_values().index[0]))
    return selected, assignment


def vif_filter(
    features: pd.DataFrame,
    threshold: float = 10.0,
) -> tuple[list[str], pd.DataFrame]:
    numeric = features.select_dtypes(include=[np.number]).copy()
    numeric = numeric.replace([np.inf, -np.inf], np.nan).fillna(numeric.median())
    columns = list(numeric.columns)
    history = []
    while len(columns) > 1:
        matrix = StandardScaler().fit_transform(numeric[columns])
        vifs = [float(variance_inflation_factor(matrix, i)) for i in range(len(columns))]
        index = int(np.nanargmax(vifs))
        maximum = vifs[index]
        history.append({"variable": columns[index], "vif": maximum})
        if np.isfinite(maximum) and maximum <= threshold:
            break
        columns.pop(index)
    return columns, pd.DataFrame(history)


def spatial_group_ids(
    longitude: Sequence[float],
    latitude: Sequence[float],
    block_size_degrees: float,
) -> np.ndarray:
    if block_size_degrees <= 0:
        raise ValueError("Spatial block size must be positive")
    lon = np.asarray(longitude, dtype=float)
    lat = np.asarray(latitude, dtype=float)
    if lon.shape != lat.shape:
        raise ValueError("Longitude and latitude shapes must match")
    gx = np.floor(lon / block_size_degrees).astype(np.int64)
    gy = np.floor(lat / block_size_degrees).astype(np.int64)
    return np.asarray([f"{x}_{y}" for x, y in zip(gx, gy, strict=True)], dtype=object)


def regression_metrics(y_true: Sequence[float], y_pred: Sequence[float]) -> dict[str, float]:
    observed = np.asarray(y_true, dtype=float)
    predicted = np.asarray(y_pred, dtype=float)
    rmse = float(np.sqrt(mean_squared_error(observed, predicted)))
    iqr = float(np.subtract(*np.nanpercentile(observed, [75, 25])))
    return {
        "r_squared": float(r2_score(observed, predicted)),
        "rmse": rmse,
        "rpiq": iqr / rmse if rmse > 0 else float("inf"),
        "bias": float(np.mean(predicted - observed)),
    }


def prediction_interval_coverage(
    y_true: Sequence[float],
    lower: Sequence[float],
    upper: Sequence[float],
) -> float:
    observed = np.asarray(y_true, dtype=float)
    low = np.asarray(lower, dtype=float)
    high = np.asarray(upper, dtype=float)
    return float(np.mean((observed >= low) & (observed <= high)))
