"""Uncertainty propagation utilities for farm and SOC aggregation.

Correlation is always supplied explicitly. The module does not assume that
pixel, field, farm, or baseline and intervention errors are independent.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class QuantileSummary:
    mean: float
    q05: float
    q50: float
    q95: float
    interval_width_90: float


def _summary(values: np.ndarray) -> QuantileSummary:
    if values.ndim != 1 or values.size == 0:
        raise ValueError("values must be a nonempty one dimensional array")
    q05, q50, q95 = np.quantile(values, [0.05, 0.50, 0.95])
    return QuantileSummary(
        mean=float(np.mean(values)),
        q05=float(q05),
        q50=float(q50),
        q95=float(q95),
        interval_width_90=float(q95 - q05),
    )


def validate_correlation_matrix(matrix: np.ndarray, size: int) -> np.ndarray:
    correlation = np.asarray(matrix, dtype=float)
    if correlation.shape != (size, size):
        raise ValueError("Correlation matrix shape does not match the variable count")
    if not np.isfinite(correlation).all():
        raise ValueError("Correlation matrix must contain finite values")
    if not np.allclose(correlation, correlation.T, atol=1e-10):
        raise ValueError("Correlation matrix must be symmetric")
    if not np.allclose(np.diag(correlation), 1.0, atol=1e-10):
        raise ValueError("Correlation matrix diagonal must equal one")
    if np.any(correlation < -1.0) or np.any(correlation > 1.0):
        raise ValueError("Correlation coefficients must be between minus one and one")
    eigenvalues = np.linalg.eigvalsh(correlation)
    if np.min(eigenvalues) < -1e-10:
        raise ValueError("Correlation matrix must be positive semidefinite")
    return correlation


def aggregate_correlated_normal(
    means: np.ndarray,
    standard_deviations: np.ndarray,
    weights: np.ndarray,
    correlation_matrix: np.ndarray,
    draws: int = 10000,
    random_state: int = 42,
) -> QuantileSummary:
    """Aggregate uncertain spatial units using an explicit correlation matrix."""

    mean_array = np.asarray(means, dtype=float)
    sd_array = np.asarray(standard_deviations, dtype=float)
    weight_array = np.asarray(weights, dtype=float)
    if mean_array.ndim != 1:
        raise ValueError("means must be one dimensional")
    if mean_array.shape != sd_array.shape or mean_array.shape != weight_array.shape:
        raise ValueError("means, standard_deviations and weights must have equal shapes")
    if mean_array.size == 0:
        raise ValueError("At least one uncertain unit is required")
    if not np.isfinite(mean_array).all() or not np.isfinite(sd_array).all():
        raise ValueError("Means and standard deviations must be finite")
    if np.any(sd_array < 0):
        raise ValueError("Standard deviations must be nonnegative")
    if np.any(~np.isfinite(weight_array)) or np.any(weight_array < 0):
        raise ValueError("Weights must be finite and nonnegative")
    if weight_array.sum() <= 0:
        raise ValueError("Weights must sum to a positive value")
    if draws < 100:
        raise ValueError("At least one hundred draws are required")

    correlation = validate_correlation_matrix(correlation_matrix, mean_array.size)
    covariance = correlation * np.outer(sd_array, sd_array)
    rng = np.random.default_rng(random_state)
    samples = rng.multivariate_normal(
        mean_array,
        covariance,
        size=draws,
        check_valid="raise",
    )
    normalized_weights = weight_array / weight_array.sum()
    aggregate = samples @ normalized_weights
    return _summary(aggregate)


def paired_scenario_difference(
    baseline_mean: float,
    baseline_sd: float,
    intervention_mean: float,
    intervention_sd: float,
    correlation: float,
    draws: int = 10000,
    random_state: int = 42,
) -> QuantileSummary:
    """Propagate uncertainty for baseline minus intervention with paired errors."""

    if baseline_sd < 0 or intervention_sd < 0:
        raise ValueError("Standard deviations must be nonnegative")
    if not -1.0 <= correlation <= 1.0:
        raise ValueError("correlation must be between minus one and one")
    matrix = np.asarray([[1.0, correlation], [correlation, 1.0]], dtype=float)
    covariance = matrix * np.outer(
        [baseline_sd, intervention_sd],
        [baseline_sd, intervention_sd],
    )
    rng = np.random.default_rng(random_state)
    samples = rng.multivariate_normal(
        [baseline_mean, intervention_mean],
        covariance,
        size=draws,
        check_valid="raise",
    )
    difference = samples[:, 0] - samples[:, 1]
    return _summary(difference)
