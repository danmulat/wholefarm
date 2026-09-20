import numpy as np
import pandas as pd

from wholefarm.soc_encoding import (
    fit_transform_oof_target_encoding,
    transform_target_encoding,
)


def test_group_aware_target_encoding_creates_numeric_features() -> None:
    frame = pd.DataFrame(
        {
            "rainfall": [800, 820, 900, 920, 1000, 1020],
            "soil_group": ["A", "A", "B", "B", "C", "C"],
        }
    )
    target = np.asarray([20, 22, 30, 32, 40, 42], dtype=float)
    groups = np.asarray(["g1", "g1", "g2", "g2", "g3", "g3"])

    encoded, bundle = fit_transform_oof_target_encoding(
        frame,
        target,
        categorical_columns=["soil_group"],
        groups=groups,
        n_splits=3,
        alpha=10.0,
    )
    assert list(encoded.columns) == ["rainfall", "__te__soil_group"]
    assert np.isfinite(encoded.to_numpy()).all()
    assert bundle.categorical_columns == ("soil_group",)


def test_unseen_category_uses_training_prior() -> None:
    frame = pd.DataFrame(
        {
            "rainfall": [800, 900, 1000, 1100],
            "soil_group": ["A", "A", "B", "B"],
        }
    )
    target = np.asarray([20, 22, 30, 32], dtype=float)
    _, bundle = fit_transform_oof_target_encoding(
        frame,
        target,
        categorical_columns=["soil_group"],
        n_splits=2,
    )
    prediction = transform_target_encoding(
        pd.DataFrame({"rainfall": [950], "soil_group": ["NEW"]}),
        bundle,
    )
    assert prediction.loc[0, "__te__soil_group"] == target.mean()
