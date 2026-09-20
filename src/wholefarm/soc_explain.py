"""Optional SHAP explainability for final digital SOC Random Forest models."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .soc_qrf import QRFModelBundle


def mean_absolute_shap(
    bundle: QRFModelBundle,
    features: pd.DataFrame,
    top_k: int | None = None,
) -> pd.DataFrame:
    """Return mean absolute SHAP values for the Random Forest mean model."""

    if top_k is not None and top_k <= 0:
        raise ValueError("top_k must be positive")
    if bundle.mean_model is None:
        raise ValueError("A fitted Random Forest mean model is required for SHAP")

    try:
        import shap
    except ImportError as exc:
        raise ImportError(
            "SOC SHAP explainability requires the optional geo dependencies"
        ) from exc

    values = bundle.transform(features)
    explainer = shap.TreeExplainer(
        bundle.mean_model,
        feature_names=list(bundle.selected_features),
    )
    shap_values = np.asarray(explainer.shap_values(values), dtype=float)
    if shap_values.ndim != 2 or shap_values.shape[1] != len(bundle.selected_features):
        raise ValueError("Unexpected SHAP output shape for SOC regression model")

    result = pd.DataFrame(
        {
            "feature": list(bundle.selected_features),
            "mean_abs_shap": np.mean(np.abs(shap_values), axis=0),
        }
    ).sort_values("mean_abs_shap", ascending=False, ignore_index=True)

    if top_k is not None:
        return result.head(top_k).reset_index(drop=True)
    return result
