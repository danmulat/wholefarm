import numpy as np
import pandas as pd

from wholefarm.soc_hybrid import (
    HybridSOCConfig,
    build_hybrid_dataset,
    compare_independent_soc_models,
    grouped_process_guided_cv,
)


def _features(groups: int, points_per_group: int) -> tuple[pd.DataFrame, np.ndarray]:
    x = []
    labels = []
    for group in range(groups):
        for point in range(points_per_group):
            value = group * 2.0 + point * 0.2
            x.append([value, value**2])
            labels.append(f"g{group}")
    return pd.DataFrame(x, columns=["climate", "management"]), np.asarray(labels)


def test_hybrid_dataset_preserves_observation_and_process_weights() -> None:
    observed, observed_groups = _features(3, 2)
    process, process_groups = _features(3, 3)
    data = build_hybrid_dataset(
        observed,
        np.arange(len(observed), dtype=float),
        observed_groups,
        process,
        np.arange(len(process), dtype=float),
        process_groups,
        process_weight=0.2,
    )
    assert len(data.features) == len(observed) + len(process)
    assert np.all(data.sample_weight[: len(observed)] == 1.0)
    assert np.all(data.sample_weight[len(observed) :] == 0.2)


def test_grouped_hybrid_cv_excludes_process_data_from_held_out_groups() -> None:
    observed, observed_groups = _features(5, 3)
    process, process_groups = _features(5, 4)
    observed_target = observed["climate"].to_numpy() * 2.0 + 10.0
    process_target = process["climate"].to_numpy() * 2.0 + 9.8

    folds, predictions = grouped_process_guided_cv(
        observed,
        observed_target,
        observed_groups,
        process,
        process_target,
        process_groups,
        HybridSOCConfig(
            process_weight=0.25,
            outer_cv=5,
            n_estimators=30,
            max_depth=6,
            min_samples_leaf=1,
            max_features=1.0,
        ),
    )
    assert len(folds) == 5
    assert len(predictions) == len(observed)
    for fold in folds:
        assert fold.n_process_train < len(process)
        assert fold.n_observed_test > 0


def test_independent_model_comparison_reports_disagreement() -> None:
    comparison = compare_independent_soc_models(
        observed_soc=[10.0, 12.0, 14.0, 16.0],
        qrf_prediction=[10.5, 11.5, 14.5, 15.5],
        rothc_prediction=[9.5, 12.5, 13.5, 16.5],
    )
    assert comparison.mean_absolute_disagreement_t_c_ha == 1.0
    assert comparison.qrf_metrics["rmse"] > 0
    assert comparison.rothc_metrics["rmse"] > 0
