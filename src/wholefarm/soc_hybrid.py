"""Research mode RothC guided machine learning for soil organic carbon.

The hybrid workflow keeps measured observations and RothC simulations distinct.
Process simulations may augment training with a lower sample weight. Spatial
validation excludes process records from held out observation groups to prevent
leakage. This module is research mode and is not automatically a Verra pathway.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GroupKFold

from .soc_qrf import regression_metrics


@dataclass(frozen=True)
class HybridSOCConfig:
    process_weight: float = 0.25
    outer_cv: int = 5
    n_estimators: int = 400
    max_depth: int | None = 20
    min_samples_leaf: int = 2
    max_features: float = 0.7
    random_state: int = 42

    def __post_init__(self) -> None:
        if not 0.0 <= self.process_weight <= 1.0:
            raise ValueError("process_weight must be between zero and one")
        if self.outer_cv < 2:
            raise ValueError("outer_cv must be at least two")
        if self.n_estimators <= 0:
            raise ValueError("n_estimators must be positive")
        if self.min_samples_leaf <= 0:
            raise ValueError("min_samples_leaf must be positive")
        if not 0.0 < self.max_features <= 1.0:
            raise ValueError("max_features must be in the interval zero to one")


@dataclass(frozen=True)
class HybridFoldResult:
    fold: int
    n_observed_train: int
    n_process_train: int
    n_observed_test: int
    held_out_groups: tuple[str, ...]
    metrics: dict[str, float]


@dataclass(frozen=True)
class HybridDataset:
    features: pd.DataFrame
    target: np.ndarray
    groups: np.ndarray
    sample_weight: np.ndarray
    source: np.ndarray


def _validate_feature_columns(
    observed_features: pd.DataFrame,
    process_features: pd.DataFrame,
) -> tuple[str, ...]:
    observed_columns = tuple(observed_features.columns)
    process_columns = tuple(process_features.columns)
    if observed_columns != process_columns:
        raise ValueError("Observed and process feature columns must match in the same order")
    if not observed_columns:
        raise ValueError("At least one feature is required")
    return observed_columns


def build_hybrid_dataset(
    observed_features: pd.DataFrame,
    observed_target: Sequence[float],
    observed_groups: Sequence[str],
    process_features: pd.DataFrame,
    process_target: Sequence[float],
    process_groups: Sequence[str],
    process_weight: float,
) -> HybridDataset:
    _validate_feature_columns(observed_features, process_features)
    if not 0.0 <= process_weight <= 1.0:
        raise ValueError("process_weight must be between zero and one")

    observed_y = np.asarray(observed_target, dtype=float)
    process_y = np.asarray(process_target, dtype=float)
    observed_group_array = np.asarray(observed_groups, dtype=object)
    process_group_array = np.asarray(process_groups, dtype=object)

    if len(observed_features) != len(observed_y):
        raise ValueError("Observed feature and target row counts must match")
    if len(observed_y) != len(observed_group_array):
        raise ValueError("Observed target and group row counts must match")
    if len(process_features) != len(process_y):
        raise ValueError("Process feature and target row counts must match")
    if len(process_y) != len(process_group_array):
        raise ValueError("Process target and group row counts must match")
    if not np.isfinite(observed_y).all() or not np.isfinite(process_y).all():
        raise ValueError("SOC targets must be finite")

    features = pd.concat(
        [observed_features.copy(), process_features.copy()],
        ignore_index=True,
    )
    target = np.concatenate([observed_y, process_y])
    groups = np.concatenate([observed_group_array, process_group_array])
    sample_weight = np.concatenate(
        [
            np.ones(len(observed_y), dtype=float),
            np.full(len(process_y), process_weight, dtype=float),
        ]
    )
    source = np.asarray(
        ["observed"] * len(observed_y) + ["rothc_process"] * len(process_y),
        dtype=object,
    )
    return HybridDataset(features, target, groups, sample_weight, source)


def _fit_hybrid_rf(
    features: pd.DataFrame,
    target: np.ndarray,
    sample_weight: np.ndarray,
    config: HybridSOCConfig,
) -> tuple[RandomForestRegressor, pd.Series]:
    numeric = features.select_dtypes(include=[np.number]).copy()
    if numeric.shape[1] != features.shape[1]:
        raise ValueError("Hybrid SOC training currently requires numeric features")
    numeric = numeric.replace([np.inf, -np.inf], np.nan)
    medians = numeric.median(numeric_only=True)
    numeric = numeric.fillna(medians)

    model = RandomForestRegressor(
        n_estimators=config.n_estimators,
        max_depth=config.max_depth,
        min_samples_leaf=config.min_samples_leaf,
        max_features=config.max_features,
        random_state=config.random_state,
        n_jobs=-1,
    )
    model.fit(numeric.to_numpy(dtype=float), target, sample_weight=sample_weight)
    return model, medians


def grouped_process_guided_cv(
    observed_features: pd.DataFrame,
    observed_target: Sequence[float],
    observed_groups: Sequence[str],
    process_features: pd.DataFrame,
    process_target: Sequence[float],
    process_groups: Sequence[str],
    config: HybridSOCConfig | None = None,
) -> tuple[list[HybridFoldResult], pd.DataFrame]:
    """Validate hybrid predictions only against held out measured observations."""

    cfg = config or HybridSOCConfig()
    _validate_feature_columns(observed_features, process_features)
    observed_y = np.asarray(observed_target, dtype=float)
    observed_group_array = np.asarray(observed_groups, dtype=object)
    process_y = np.asarray(process_target, dtype=float)
    process_group_array = np.asarray(process_groups, dtype=object)

    if len(observed_features) != len(observed_y):
        raise ValueError("Observed feature and target row counts must match")
    if len(process_features) != len(process_y):
        raise ValueError("Process feature and target row counts must match")

    unique_groups = int(pd.Series(observed_group_array).nunique())
    splits = min(cfg.outer_cv, unique_groups)
    if splits < 2:
        raise ValueError("At least two observed spatial groups are required")

    folds: list[HybridFoldResult] = []
    prediction_frames: list[pd.DataFrame] = []
    splitter = GroupKFold(n_splits=splits)

    for fold, (train_index, test_index) in enumerate(
        splitter.split(
            observed_features,
            observed_y,
            groups=observed_group_array,
        ),
        start=1,
    ):
        held_out = set(str(value) for value in observed_group_array[test_index])
        process_mask = np.asarray(
            [str(value) not in held_out for value in process_group_array],
            dtype=bool,
        )

        train_dataset = build_hybrid_dataset(
            observed_features.iloc[train_index],
            observed_y[train_index],
            observed_group_array[train_index],
            process_features.loc[process_mask],
            process_y[process_mask],
            process_group_array[process_mask],
            cfg.process_weight,
        )
        model, medians = _fit_hybrid_rf(
            train_dataset.features,
            train_dataset.target,
            train_dataset.sample_weight,
            cfg,
        )

        test_frame = observed_features.iloc[test_index].copy()
        test_frame = test_frame.replace([np.inf, -np.inf], np.nan).fillna(medians)
        prediction = model.predict(test_frame.to_numpy(dtype=float))
        metrics = regression_metrics(observed_y[test_index], prediction)
        held_out_sorted = tuple(sorted(held_out))
        folds.append(
            HybridFoldResult(
                fold=fold,
                n_observed_train=len(train_index),
                n_process_train=int(process_mask.sum()),
                n_observed_test=len(test_index),
                held_out_groups=held_out_sorted,
                metrics=metrics,
            )
        )
        prediction_frames.append(
            pd.DataFrame(
                {
                    "row_index": observed_features.index[test_index],
                    "fold": fold,
                    "observed_soc": observed_y[test_index],
                    "predicted_soc": prediction,
                }
            )
        )

    return folds, pd.concat(prediction_frames, ignore_index=True)


@dataclass(frozen=True)
class IndependentSOCComparison:
    qrf_metrics: dict[str, float]
    rothc_metrics: dict[str, float]
    mean_absolute_disagreement_t_c_ha: float
    median_absolute_disagreement_t_c_ha: float


def compare_independent_soc_models(
    observed_soc: Sequence[float],
    qrf_prediction: Sequence[float],
    rothc_prediction: Sequence[float],
) -> IndependentSOCComparison:
    observed = np.asarray(observed_soc, dtype=float)
    qrf = np.asarray(qrf_prediction, dtype=float)
    rothc = np.asarray(rothc_prediction, dtype=float)
    if not (observed.shape == qrf.shape == rothc.shape):
        raise ValueError("Observed, QRF and RothC arrays must have equal shapes")
    disagreement = np.abs(qrf - rothc)
    return IndependentSOCComparison(
        qrf_metrics=regression_metrics(observed, qrf),
        rothc_metrics=regression_metrics(observed, rothc),
        mean_absolute_disagreement_t_c_ha=float(np.mean(disagreement)),
        median_absolute_disagreement_t_c_ha=float(np.median(disagreement)),
    )
