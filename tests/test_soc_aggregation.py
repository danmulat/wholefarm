import pandas as pd
import pytest

from wholefarm.soc_aggregation import aggregate_soc_by_group, aggregate_soc_pixels


def _predictions() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "predicted_mean": [10.0, 20.0, 30.0],
            "q05": [8.0, 18.0, 28.0],
            "q50": [10.0, 20.0, 30.0],
            "q95": [12.0, 22.0, 32.0],
        }
    )


def test_pixel_soc_aggregation_is_area_weighted() -> None:
    summary = aggregate_soc_pixels(_predictions(), [1.0, 2.0, 1.0])
    assert summary.area_ha == 4.0
    assert summary.mean_soc_t_c_ha == pytest.approx(20.0)
    assert summary.mean_soc_total_t_c == pytest.approx(80.0)
    assert summary.mean_soc_total_t_co2e == pytest.approx(80.0 * 44.0 / 12.0)


def test_group_aggregation_supports_field_or_basin_units() -> None:
    result = aggregate_soc_by_group(
        _predictions(),
        [1.0, 2.0, 1.0],
        ["field_1", "field_1", "field_2"],
    )
    field_1 = result.loc[result["group_id"] == "field_1"].iloc[0]
    field_2 = result.loc[result["group_id"] == "field_2"].iloc[0]
    assert field_1["area_ha"] == 3.0
    assert field_1["mean_soc_t_c_ha"] == pytest.approx(50.0 / 3.0)
    assert field_2["mean_soc_total_t_c"] == 30.0
