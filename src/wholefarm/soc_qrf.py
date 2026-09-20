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
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_selection import RFECV
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, GroupKFold
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.outliers_influence import variance_inflation_factor

DEFAULT_QUANTILES = tuple(range(5, 100, 5))
DEFAULT_PARAM_GRID = {
    "n_estimators": [200, 400, 600],
    "max_depth": [10, 20, 30],
    "min_samples_split": [2, 5, 10],
    "min_samples_leaf": [1, 2, 4],
    "max_features": [0.5, 0.7, 1.0],
}


@dataclass(frozen=True)
class QRFWorkflowConfig:
    outer_cv: int = 5
    inner_cv: int = 3
    correlation_distance_threshold: float = 0.2
    vif_threshold: float = 10.0
    minimum_soc_depth_cm: float = 30.0
    random_state: int = 42
    scale_numeric_features: bool = True
    rfecv_min_fraction: float = 0.10
    rfecv_min_absolute: int = 8
    quantiles: tuple[int, ...] = DEFAULT_QUANTILES

    def __post_init__(self) -> None:
        if self.minimum_soc_depth_cm < 30.0:
            raise ValueError("VM0042 SOC quantification depth must be at least 30 cm")
        if self.outer_cv < 2 or self.inner_cv < 2:
            raise ValueError("Cross validation fold counts must be at least two")
        if not 0 < self.rfecv_min_fraction <= 1:
            raise ValueError("rfecv_min_fraction must be in the interval zero to one")
        if self.rfecv_min_absolute < 1:
            raise ValueError("rfecv_min_absolute must be positive")


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


@dataclass(frozen=True)
class QRFOuterFoldResult:
    fold: int
    n_train: int
    n_test: int
    selected_features: tuple[str, ...]
    best_params: dict[str, float | int]
    metrics: dict[str, float]


@dataclass
class QRFModelBundle:
    model: object
    selected_features: tuple[str, ...]
    medians: pd.Series
    scaler: StandardScaler | None
    best_params: dict[str, float | int]

    def transform(self, features: pd.DataFrame) -> np.ndarray:
        frame = features.loc[:, list(self.selected_features)].copy()
        frame = frame.replace([np.inf, -np.inf], np.nan).fillna(self.medians)
        values = frame.to_numpy(dtype=float)
        if self.scaler is not None:
            values = self.scaler.transform(values)
        return values

    def predict_quantiles(
        self,
        features: pd.DataFrame,
        quantiles: Sequence[float] = (0.05, 0.50, 0.95),
    ) -> pd.DataFrame:
        values = self.transform(features)
        prediction = np.asarray(
            self.model.predict(values, quantiles=list(quantiles)),
            dtype=float,
        )
        if prediction.ndim == 1:
            prediction = prediction[:, None]
        columns = [f"q{int(round(q * 100)):02d}" for q in quantiles]
        return pd.DataFrame(prediction, columns=columns, index=features.index)


def _qrf_class():
    try:
        from quantile_forest import RandomForestQuantileRegressor
    except ImportError as exc:
        raise ImportError(
            "Quantile Regression Forest modeling requires the quantile-forest package"
        ) from exc
    return RandomForestQuantileRegressor


def _prepare_numeric_features(features: pd.DataFrame) -> pd.DataFrame:
    numeric = features.select_dtypes(include=[np.number]).copy()
    if numeric.empty:
        raise ValueError("At least one numeric feature is required")
    numeric = numeric.replace([np.inf, -np.inf], np.nan)
    return numeric


def nested_spatial_qrf_cv(
    features: pd.DataFrame,
    target: Sequence[float],
    groups: Sequence[str],
    config: QRFWorkflowConfig | None = None,
    param_grid: dict[str, list[float | int]] | None = None,
) -> tuple[list[QRFOuterFoldResult], pd.DataFrame]:
    """Run nested spatial validation following the reference QRF modeling structure."""

    cfg = config or QRFWorkflowConfig()
    x = _prepare_numeric_features(features)
    y = np.asarray(target, dtype=float)
    group_array = np.asarray(groups, dtype=object)

    if len(x) != len(y) or len(y) != len(group_array):
        raise ValueError("Features, target, and groups must have equal row counts")
    if not np.isfinite(y).all():
        raise ValueError("Target values must all be finite")

    unique_groups = int(pd.Series(group_array).nunique())
    outer_splits = min(cfg.outer_cv, unique_groups)
    if outer_splits < 2:
        raise ValueError("At least two spatial groups are required")

    outer_cv = GroupKFold(n_splits=outer_splits)
    qrf_type = _qrf_class()
    results: list[QRFOuterFoldResult] = []
    prediction_rows: list[pd.DataFrame] = []

    for fold, (train_idx, test_idx) in enumerate(
        outer_cv.split(x, y, groups=group_array),
        start=1,
    ):
        x_train = x.iloc[train_idx].copy()
        x_test = x.iloc[test_idx].copy()
        y_train = y[train_idx]
        y_test = y[test_idx]
        train_groups = group_array[train_idx]

        medians = x_train.median(numeric_only=True)
        x_train = x_train.fillna(medians)
        x_test = x_test.fillna(medians)

        scaler = StandardScaler() if cfg.scale_numeric_features else None
        if scaler is None:
            train_values = x_train.to_numpy(dtype=float)
            test_values = x_test.to_numpy(dtype=float)
        else:
            train_values = scaler.fit_transform(x_train)
            test_values = scaler.transform(x_test)

        inner_group_count = int(pd.Series(train_groups).nunique())
        inner_splits = min(cfg.inner_cv, inner_group_count)
        if inner_splits < 2:
            raise ValueError("Each outer training fold needs at least two spatial groups")
        inner_cv = GroupKFold(n_splits=inner_splits)

        min_features = max(
            cfg.rfecv_min_absolute,
            int(np.ceil(cfg.rfecv_min_fraction * x_train.shape[1])),
        )
        min_features = min(min_features, x_train.shape[1])

        selector = RFECV(
            estimator=RandomForestRegressor(
                n_estimators=200,
                random_state=cfg.random_state,
                n_jobs=-1,
            ),
            step=1,
            min_features_to_select=min_features,
            cv=inner_cv,
            scoring="neg_root_mean_squared_error",
            n_jobs=-1,
        )
        selector.fit(train_values, y_train, groups=train_groups)

        selected_features = tuple(x_train.columns[selector.support_])
        selected_train = train_values[:, selector.support_]
        selected_test = test_values[:, selector.support_]

        tuner = GridSearchCV(
            estimator=RandomForestRegressor(
                random_state=cfg.random_state,
                n_jobs=-1,
            ),
            param_grid=param_grid or DEFAULT_PARAM_GRID,
            cv=inner_cv,
            scoring="neg_root_mean_squared_error",
            n_jobs=-1,
        )
        tuner.fit(selected_train, y_train, groups=train_groups)
        best_params = dict(tuner.best_params_)

        qrf = qrf_type(
            random_state=cfg.random_state,
            n_jobs=-1,
            **best_params,
        )
        qrf.fit(selected_train, y_train)

        mean_prediction = np.asarray(qrf.predict(selected_test), dtype=float)
        quantile_prediction = np.asarray(
            qrf.predict(selected_test, quantiles=[0.05, 0.50, 0.95]),
            dtype=float,
        )
        if quantile_prediction.ndim == 1:
            quantile_prediction = quantile_prediction[:, None]

        q05 = quantile_prediction[:, 0]
        q50 = quantile_prediction[:, 1]
        q95 = quantile_prediction[:, 2]
        metrics = regression_metrics(y_test, mean_prediction)
        metrics["picp_90"] = prediction_interval_coverage(y_test, q05, q95)
        metrics["mean_pi_width_90"] = float(np.mean(q95 - q05))

        results.append(
            QRFOuterFoldResult(
                fold=fold,
                n_train=len(train_idx),
                n_test=len(test_idx),
                selected_features=selected_features,
                best_params=best_params,
                metrics=metrics,
            )
        )
        prediction_rows.append(
            pd.DataFrame(
                {
                    "row_index": x.index[test_idx],
                    "fold": fold,
                    "observed": y_test,
                    "predicted_mean": mean_prediction,
                    "q05": q05,
                    "q50": q50,
                    "q95": q95,
                    "interval_width_90": q95 - q05,
                }
            )
        )

    predictions = pd.concat(prediction_rows, ignore_index=True)
    return results, predictions


def fit_final_qrf(
    features: pd.DataFrame,
    target: Sequence[float],
    groups: Sequence[str],
    config: QRFWorkflowConfig | None = None,
    param_grid: dict[str, list[float | int]] | None = None,
) -> QRFModelBundle:
    """Fit a final QRF after group aware feature selection and tuning."""

    cfg = config or QRFWorkflowConfig()
    x = _prepare_numeric_features(features)
    y = np.asarray(target, dtype=float)
    group_array = np.asarray(groups, dtype=object)
    if len(x) != len(y) or len(y) != len(group_array):
        raise ValueError("Features, target, and groups must have equal row counts")

    medians = x.median(numeric_only=True)
    x = x.fillna(medians)
    scaler = StandardScaler() if cfg.scale_numeric_features else None
    values = scaler.fit_transform(x) if scaler is not None else x.to_numpy(dtype=float)

    n_groups = int(pd.Series(group_array).nunique())
    inner_splits = min(cfg.inner_cv, n_groups)
    if inner_splits < 2:
        raise ValueError("At least two spatial groups are required")
    inner_cv = GroupKFold(n_splits=inner_splits)

    min_features = max(
        cfg.rfecv_min_absolute,
        int(np.ceil(cfg.rfecv_min_fraction * x.shape[1])),
    )
    min_features = min(min_features, x.shape[1])

    selector = RFECV(
        estimator=RandomForestRegressor(
            n_estimators=200,
            random_state=cfg.random_state,
            n_jobs=-1,
        ),
        step=1,
        min_features_to_select=min_features,
        cv=inner_cv,
        scoring="neg_root_mean_squared_error",
        n_jobs=-1,
    )
    selector.fit(values, y, groups=group_array)
    selected_features = tuple(x.columns[selector.support_])
    selected_values = values[:, selector.support_]

    tuner = GridSearchCV(
        estimator=RandomForestRegressor(
            random_state=cfg.random_state,
            n_jobs=-1,
        ),
        param_grid=param_grid or DEFAULT_PARAM_GRID,
        cv=inner_cv,
        scoring="neg_root_mean_squared_error",
        n_jobs=-1,
    )
    tuner.fit(selected_values, y, groups=group_array)

    qrf_type = _qrf_class()
    model = qrf_type(
        random_state=cfg.random_state,
        n_jobs=-1,
        **dict(tuner.best_params_),
    )
    model.fit(selected_values, y)

    selected_medians = medians.loc[list(selected_features)]
    if scaler is not None:
        selected_scaler = StandardScaler()
        selected_scaler.fit(x.loc[:, list(selected_features)])
        selected_training = selected_scaler.transform(
            x.loc[:, list(selected_features)]
        )
        model.fit(selected_training, y)
    else:
        selected_scaler = None

    return QRFModelBundle(
        model=model,
        selected_features=selected_features,
        medians=selected_medians,
        scaler=selected_scaler,
        best_params=dict(tuner.best_params_),
    )
