import numpy as np
import pandas as pd

from wholefarm.soc_qrf import (
    QRFWorkflowConfig,
    fit_final_qrf,
    nested_spatial_qrf_cv,
)


def _categorical_soc_data() -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(77)
    n = 48
    categories = np.asarray(["vertisol", "nitisol", "cambisol"] * 16, dtype=object)
    frame = pd.DataFrame(
        {
            "rainfall": rng.normal(1050, 120, n),
            "clay": rng.uniform(20, 55, n),
            "soil_group": categories,
        }
    )
    category_effect = pd.Series(categories).map(
        {"vertisol": 8.0, "nitisol": 4.0, "cambisol": 0.0}
    ).to_numpy(dtype=float)
    target = (
        0.02 * frame["rainfall"].to_numpy()
        + 0.35 * frame["clay"].to_numpy()
        + category_effect
        + rng.normal(0, 1.0, n)
    )
    groups = np.asarray([f"g{i // 8}" for i in range(n)], dtype=object)
    return frame, target, groups


def _small_grid() -> dict[str, list[float | int]]:
    return {
        "n_estimators": [20],
        "max_depth": [5],
        "min_samples_split": [2],
        "min_samples_leaf": [1],
        "max_features": [1.0],
    }


def test_nested_qrf_target_encodes_categories_inside_spatial_folds() -> None:
    frame, target, groups = _categorical_soc_data()
    folds, predictions = nested_spatial_qrf_cv(
        frame,
        target,
        groups,
        config=QRFWorkflowConfig(
            outer_cv=3,
            inner_cv=2,
            rfecv_min_absolute=1,
            scale_numeric_features=True,
        ),
        param_grid=_small_grid(),
        categorical_columns=["soil_group"],
    )
    assert len(folds) == 3
    assert len(predictions) == len(frame)
    for fold in folds:
        assert "soil_group" not in fold.selected_features
        assert all(
            feature in {"rainfall", "clay", "__te__soil_group"}
            for feature in fold.selected_features
        )


def test_final_qrf_handles_unseen_raw_category_with_training_prior() -> None:
    frame, target, groups = _categorical_soc_data()
    bundle = fit_final_qrf(
        frame,
        target,
        groups,
        config=QRFWorkflowConfig(
            inner_cv=2,
            rfecv_min_absolute=1,
            scale_numeric_features=True,
        ),
        param_grid=_small_grid(),
        categorical_columns=["soil_group"],
    )
    prediction_frame = pd.DataFrame(
        {
            "rainfall": [1000.0, 1100.0],
            "clay": [30.0, 40.0],
            "soil_group": ["unseen_soil", "vertisol"],
        }
    )
    mean = bundle.predict_mean(prediction_frame)
    quantiles = bundle.predict_quantiles(prediction_frame)
    assert bundle.target_encoding_bundle is not None
    assert np.isfinite(mean.to_numpy()).all()
    assert np.isfinite(quantiles.to_numpy()).all()
    assert (quantiles["q95"] >= quantiles["q05"]).all()
