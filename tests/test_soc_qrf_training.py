import numpy as np
import pandas as pd

from wholefarm.soc_qrf import (
    QRFWorkflowConfig,
    fit_final_qrf,
    nested_spatial_qrf_cv,
)


def _synthetic_soc_data() -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(42)
    n = 40
    frame = pd.DataFrame(
        {
            "rainfall": rng.normal(1000, 150, n),
            "temperature": rng.normal(20, 2, n),
            "clay": rng.uniform(15, 55, n),
            "ndvi": rng.uniform(0.2, 0.8, n),
            "elevation": rng.uniform(900, 2200, n),
            "slope": rng.uniform(0, 20, n),
        }
    )
    target = (
        0.025 * frame["rainfall"].to_numpy()
        - 0.5 * frame["temperature"].to_numpy()
        + 0.4 * frame["clay"].to_numpy()
        + rng.normal(0, 2, n)
    )
    groups = np.asarray([f"g{i // 5}" for i in range(n)], dtype=object)
    return frame, target, groups


def test_nested_spatial_qrf_outputs_quantile_intervals() -> None:
    frame, target, groups = _synthetic_soc_data()
    config = QRFWorkflowConfig(
        outer_cv=4,
        inner_cv=2,
        rfecv_min_absolute=2,
        scale_numeric_features=True,
    )
    small_grid = {
        "n_estimators": [20],
        "max_depth": [5],
        "min_samples_split": [2],
        "min_samples_leaf": [1],
        "max_features": [0.7],
    }
    folds, predictions = nested_spatial_qrf_cv(
        frame,
        target,
        groups,
        config=config,
        param_grid=small_grid,
    )
    assert len(folds) == 4
    assert len(predictions) == len(frame)
    assert {
        "q05",
        "q10",
        "q50",
        "q90",
        "q95",
        "interval_width_90",
    }.issubset(predictions.columns)
    assert (predictions["q95"] >= predictions["q05"]).all()
    assert "picp_90" in folds[0].metrics
    assert "picp_80" in folds[0].metrics


def test_final_qrf_predicts_requested_quantiles() -> None:
    frame, target, groups = _synthetic_soc_data()
    config = QRFWorkflowConfig(
        outer_cv=4,
        inner_cv=2,
        rfecv_min_absolute=2,
    )
    small_grid = {
        "n_estimators": [20],
        "max_depth": [5],
        "min_samples_split": [2],
        "min_samples_leaf": [1],
        "max_features": [0.7],
    }
    bundle = fit_final_qrf(
        frame,
        target,
        groups,
        config=config,
        param_grid=small_grid,
    )
    prediction = bundle.predict_quantiles(frame.iloc[:3])
    assert list(prediction.columns) == ["q05", "q50", "q95"]
    assert prediction.shape == (3, 3)