"""Group aware target encoding used by the digital SOC workflow.

The implementation follows the pinned Florida SOC reference pattern. Categorical
features are encoded out of fold during model development. Final mappings are
then fit on the full training data for prediction on new observations or raster
category bands.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold, KFold


@dataclass(frozen=True)
class CategoryEncoder:
    mapping: dict[object, float]
    prior: float
    alpha: float


@dataclass(frozen=True)
class TargetEncodingBundle:
    encoders: dict[str, CategoryEncoder]
    numeric_medians: dict[str, float]
    categorical_columns: tuple[str, ...]
    numeric_columns: tuple[str, ...]
    encoded_feature_names: tuple[str, ...]


def _normalize_category(series: pd.Series) -> pd.Series:
    result = series.astype(object)
    return result.where(result.notna(), "__NA__")


def _mean_encode_series(
    categories: pd.Series,
    target: pd.Series,
    alpha: float,
    prior: float,
) -> dict[object, float]:
    if alpha < 0:
        raise ValueError("alpha must be nonnegative")
    frame = pd.DataFrame(
        {
            "category": _normalize_category(categories).to_numpy(),
            "target": target.to_numpy(dtype=float),
        }
    )
    grouped = frame.groupby("category", dropna=False)["target"].agg(["mean", "count"])
    encoded = (
        grouped["count"] * grouped["mean"] + alpha * prior
    ) / (grouped["count"] + alpha)
    return {key: float(value) for key, value in encoded.to_dict().items()}


def fit_transform_oof_target_encoding(
    features: pd.DataFrame,
    target: Sequence[float],
    categorical_columns: Sequence[str],
    groups: Sequence[str] | None = None,
    n_splits: int = 5,
    alpha: float = 10.0,
    random_state: int = 42,
) -> tuple[pd.DataFrame, TargetEncodingBundle]:
    if n_splits < 2:
        raise ValueError("n_splits must be at least two")
    if alpha < 0:
        raise ValueError("alpha must be nonnegative")

    frame = features.copy().reset_index(drop=True)
    y = pd.Series(np.asarray(target, dtype=float)).reset_index(drop=True)
    if len(frame) != len(y):
        raise ValueError("Features and target must have equal row counts")
    if not np.isfinite(y.to_numpy()).all():
        raise ValueError("Target values must be finite")

    cat_cols = tuple(column for column in categorical_columns if column in frame.columns)
    missing_requested = set(categorical_columns).difference(frame.columns)
    if missing_requested:
        raise ValueError(f"Missing categorical columns: {sorted(missing_requested)}")
    num_cols = tuple(column for column in frame.columns if column not in cat_cols)

    for column in cat_cols:
        frame[column] = _normalize_category(frame[column])

    if num_cols:
        numeric = frame.loc[:, list(num_cols)].apply(pd.to_numeric, errors="coerce")
        numeric = numeric.replace([np.inf, -np.inf], np.nan)
        medians = numeric.median(numeric_only=True)
        numeric = numeric.fillna(medians)
        frame.loc[:, list(num_cols)] = numeric
        numeric_medians = {key: float(value) for key, value in medians.items()}
    else:
        numeric_medians = {}

    prior = float(y.mean())
    encoded_columns = [f"__te__{column}" for column in cat_cols]
    for column in encoded_columns:
        frame[column] = np.nan

    group_array = None if groups is None else np.asarray(groups, dtype=object)
    if group_array is not None and len(group_array) != len(frame):
        raise ValueError("Groups must have the same row count as features")

    use_group = (
        group_array is not None
        and int(pd.Series(group_array).nunique()) >= 2
    )
    if use_group:
        n_unique_groups = int(pd.Series(group_array).nunique())
        n_splits_eff = min(n_splits, n_unique_groups)
        splitter = GroupKFold(n_splits=n_splits_eff)
        splits = splitter.split(frame, y, groups=group_array)
    else:
        n_splits_eff = min(n_splits, len(frame))
        if n_splits_eff < 2:
            raise ValueError("At least two rows are required for target encoding")
        splitter = KFold(
            n_splits=n_splits_eff,
            shuffle=True,
            random_state=random_state,
        )
        splits = splitter.split(frame)

    for train_index, valid_index in splits:
        training = frame.iloc[train_index]
        training_y = y.iloc[train_index]
        validation = frame.iloc[valid_index]

        for column in cat_cols:
            mapping = _mean_encode_series(
                training[column],
                training_y,
                alpha,
                prior,
            )
            encoded = (
                validation[column]
                .map(mapping)
                .astype(float)
                .fillna(prior)
                .to_numpy()
            )
            frame.iloc[
                valid_index,
                frame.columns.get_loc(f"__te__{column}"),
            ] = encoded

    for column in encoded_columns:
        frame[column] = frame[column].astype(float).fillna(prior)

    encoders: dict[str, CategoryEncoder] = {}
    for column in cat_cols:
        mapping = _mean_encode_series(frame[column], y, alpha, prior)
        encoders[column] = CategoryEncoder(mapping=mapping, prior=prior, alpha=alpha)

    encoded_names = tuple(num_cols) + tuple(encoded_columns)
    encoded_frame = pd.concat(
        [
            frame.loc[:, list(num_cols)].astype(float) if num_cols else pd.DataFrame(index=frame.index),
            frame.loc[:, encoded_columns].astype(float) if encoded_columns else pd.DataFrame(index=frame.index),
        ],
        axis=1,
    )
    encoded_frame.columns = list(encoded_names)

    bundle = TargetEncodingBundle(
        encoders=encoders,
        numeric_medians=numeric_medians,
        categorical_columns=cat_cols,
        numeric_columns=num_cols,
        encoded_feature_names=encoded_names,
    )
    return encoded_frame, bundle


def transform_target_encoding(
    features: pd.DataFrame,
    bundle: TargetEncodingBundle,
) -> pd.DataFrame:
    required = set(bundle.numeric_columns) | set(bundle.categorical_columns)
    missing = required.difference(features.columns)
    if missing:
        raise ValueError(f"Missing prediction columns: {sorted(missing)}")

    frame = features.copy().reset_index(drop=True)
    output = pd.DataFrame(index=frame.index)

    for column in bundle.numeric_columns:
        values = pd.to_numeric(frame[column], errors="coerce")
        values = values.replace([np.inf, -np.inf], np.nan)
        output[column] = values.fillna(bundle.numeric_medians[column]).astype(float)

    for column in bundle.categorical_columns:
        encoder = bundle.encoders[column]
        normalized = _normalize_category(frame[column])
        output[f"__te__{column}"] = (
            normalized.map(encoder.mapping).astype(float).fillna(encoder.prior)
        )

    return output.loc[:, list(bundle.encoded_feature_names)]