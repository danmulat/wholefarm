import numpy as np
import pandas as pd

from wholefarm.soc_encoding import CategoryEncoder, TargetEncodingBundle
from wholefarm.soc_mapping import (
    predict_soc_block,
    predict_soc_table,
    summarize_soc_predictions,
)
from wholefarm.soc_qrf import QRFModelBundle


class FakeQRF:
    def predict(self, values, quantiles=None):
        base = values[:, 0] + 2.0 * values[:, 1]
        if quantiles is None:
            return base
        offsets = {
            0.05: -2.0,
            0.50: 0.0,
            0.95: 2.0,
        }
        return np.column_stack([base + offsets[float(q)] for q in quantiles])


class FakeMeanRF:
    def predict(self, values):
        return values[:, 0] + 2.0 * values[:, 1] + 0.5


def _bundle() -> QRFModelBundle:
    return QRFModelBundle(
        model=FakeQRF(),
        selected_features=("rainfall", "clay"),
        medians=pd.Series({"rainfall": 10.0, "clay": 2.0}),
        scaler=None,
        best_params={},
        mean_model=FakeMeanRF(),
    )


def test_table_prediction_uses_rf_mean_and_qrf_intervals() -> None:
    frame = pd.DataFrame({"rainfall": [10.0, 20.0], "clay": [2.0, 3.0]})
    result = predict_soc_table(_bundle(), frame)
    assert list(result.columns) == [
        "predicted_mean",
        "q05",
        "q50",
        "q95",
        "interval_width_90",
    ]
    assert result.loc[0, "predicted_mean"] == 14.5
    assert result.loc[0, "q50"] == 14.0
    assert result.loc[0, "interval_width_90"] == 4.0


def test_block_prediction_masks_nodata_and_keeps_reference_outputs() -> None:
    stack = np.asarray(
        [
            [[10.0, -9999.0], [20.0, 30.0]],
            [[2.0, 3.0], [4.0, 5.0]],
        ],
        dtype=np.float32,
    )
    result = predict_soc_block(
        _bundle(),
        stack,
        ("rainfall", "clay"),
        nodata_value=-9999.0,
    )
    assert result.valid_mask.sum() == 3
    assert result.mean[0, 0] == 14.5
    assert result.mean[0, 1] == -9999.0
    assert result.q95[1, 0] > result.q05[1, 0]


def test_area_summary_is_weighted_surface_summary() -> None:
    frame = pd.DataFrame(
        {
            "predicted_mean": [10.0, 20.0],
            "q05": [8.0, 18.0],
            "q50": [10.0, 20.0],
            "q95": [12.0, 22.0],
            "interval_width_90": [4.0, 4.0],
        }
    )
    summary = summarize_soc_predictions(frame, weights=[1.0, 3.0])
    assert summary.mean_soc_t_c_ha == 17.5
    assert summary.q05_surface_mean_t_c_ha == 15.5
    assert summary.n_valid == 2


def _encoded_bundle() -> QRFModelBundle:
    encoding = TargetEncodingBundle(
        encoders={
            "soil_group": CategoryEncoder(
                mapping={1.0: 5.0, 2.0: 10.0},
                prior=7.5,
                alpha=10.0,
            )
        },
        numeric_medians={"rainfall": 10.0},
        categorical_columns=("soil_group",),
        numeric_columns=("rainfall",),
        encoded_feature_names=("rainfall", "__te__soil_group"),
    )
    return QRFModelBundle(
        model=FakeQRF(),
        selected_features=("rainfall", "__te__soil_group"),
        medians=pd.Series({"rainfall": 10.0, "__te__soil_group": 7.5}),
        scaler=None,
        best_params={},
        mean_model=FakeMeanRF(),
        target_encoding_bundle=encoding,
    )


def test_block_prediction_accepts_raw_categorical_raster_band() -> None:
    stack = np.asarray(
        [
            [[10.0, 20.0], [30.0, 40.0]],
            [[1.0, 2.0], [99.0, 1.0]],
        ],
        dtype=np.float32,
    )
    result = predict_soc_block(
        _encoded_bundle(),
        stack,
        ("rainfall", "soil_group"),
    )
    assert result.valid_mask.sum() == 4
    assert result.mean[0, 0] == 20.5
    assert result.mean[0, 1] == 40.5
    assert result.mean[1, 0] == 45.5
    assert result.q95[1, 1] > result.q05[1, 1]