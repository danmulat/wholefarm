import numpy as np
import pytest

from wholefarm.uncertainty import (
    aggregate_correlated_normal,
    paired_scenario_difference,
    validate_correlation_matrix,
)


def test_spatial_uncertainty_uses_explicit_correlation() -> None:
    means = np.asarray([20.0, 30.0])
    sds = np.asarray([2.0, 2.0])
    weights = np.asarray([1.0, 1.0])
    independent = aggregate_correlated_normal(
        means,
        sds,
        weights,
        np.eye(2),
        draws=5000,
        random_state=1,
    )
    correlated = aggregate_correlated_normal(
        means,
        sds,
        weights,
        np.asarray([[1.0, 0.9], [0.9, 1.0]]),
        draws=5000,
        random_state=1,
    )
    assert independent.mean == pytest.approx(25.0, abs=0.1)
    assert correlated.interval_width_90 > independent.interval_width_90


def test_paired_scenario_difference_respects_shared_error() -> None:
    independent = paired_scenario_difference(
        100.0,
        10.0,
        80.0,
        10.0,
        correlation=0.0,
        draws=5000,
        random_state=2,
    )
    paired = paired_scenario_difference(
        100.0,
        10.0,
        80.0,
        10.0,
        correlation=0.9,
        draws=5000,
        random_state=2,
    )
    assert paired.mean == pytest.approx(20.0, abs=0.2)
    assert paired.interval_width_90 < independent.interval_width_90


def test_invalid_correlation_matrix_is_rejected() -> None:
    with pytest.raises(ValueError):
        validate_correlation_matrix(np.asarray([[1.0, 1.2], [1.2, 1.0]]), 2)
