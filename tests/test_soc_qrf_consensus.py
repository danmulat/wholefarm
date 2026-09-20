import numpy as np
import pandas as pd

from wholefarm.soc_qrf import (
    QRFOuterFoldResult,
    consensus_best_params,
    consensus_features,
    fit_consensus_qrf,
)


def _fold(
    fold: int,
    features: tuple[str, ...],
    n_estimators: int,
    rpiq: float,
) -> QRFOuterFoldResult:
    return QRFOuterFoldResult(
        fold=fold,
        n_train=20,
        n_test=5,
        selected_features=features,
        best_params={
            "n_estimators": n_estimators,
            "max_depth": 5,
            "min_samples_split": 2,
            "min_samples_leaf": 1,
            "max_features": 1.0,
        },
        metrics={"rpiq": rpiq, "rmse": 1.0, "r_squared": 0.5},
    )


def test_fold_consensus_features_and_parameter_modes() -> None:
    folds = [
        _fold(1, ("rainfall", "clay", "ndvi"), 20, 1.1),
        _fold(2, ("rainfall", "clay"), 30, 1.4),
        _fold(3, ("rainfall", "clay", "slope"), 30, 1.2),
    ]
    assert consensus_features(folds, minimum_fold_count=2) == ("rainfall", "clay")
    params = consensus_best_params(folds)
    assert params["n_estimators"] == 30
    assert params["max_depth"] == 5


def test_consensus_final_model_predicts_mean_and_quantiles() -> None:
    rng = np.random.default_rng(123)
    frame = pd.DataFrame(
        {
            "rainfall": rng.normal(1000, 100, 30),
            "clay": rng.uniform(20, 50, 30),
            "ndvi": rng.uniform(0.2, 0.8, 30),
        }
    )
    target = (
        frame["rainfall"].to_numpy() * 0.02
        + frame["clay"].to_numpy() * 0.4
        + rng.normal(0, 1, 30)
    )
    folds = [
        _fold(1, ("rainfall", "clay"), 20, 1.1),
        _fold(2, ("rainfall", "clay"), 20, 1.2),
        _fold(3, ("rainfall", "clay", "ndvi"), 20, 1.0),
    ]
    bundle = fit_consensus_qrf(
        frame,
        target,
        folds,
        minimum_fold_count=2,
    )
    mean = bundle.predict_mean(frame.iloc[:4])
    quantiles = bundle.predict_quantiles(frame.iloc[:4])
    assert len(mean) == 4
    assert list(quantiles.columns) == ["q05", "q50", "q95"]
    assert (quantiles["q95"] >= quantiles["q05"]).all()
