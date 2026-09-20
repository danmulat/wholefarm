import pytest

from wholefarm.soc_stock import SoilLayer, aggregate_soc_layers_t_c_ha, validate_vm0042_depth


def test_quantification_requires_30_cm() -> None:
    with pytest.raises(ValueError):
        validate_vm0042_depth(20.0)


def test_shallow_legacy_data_can_be_used_with_documented_extrapolation() -> None:
    validate_vm0042_depth(
        20.0,
        purpose="calibration_validation",
        extrapolation_method="locally validated depth function",
    )


def test_layers_aggregate_to_30_cm() -> None:
    layers = [
        SoilLayer(20.0, 1.2, 0.0, 10.0, 5.0),
        SoilLayer(15.0, 1.3, 10.0, 30.0, 10.0),
    ]
    assert aggregate_soc_layers_t_c_ha(layers) > 0
