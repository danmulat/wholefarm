from wholefarm.gleam_weights import (
    calc_avg_weights,
    calc_cohort_weights,
    calc_daily_weight_gain,
)


def test_cohort_weights_reference_juvenile() -> None:
    result = calc_cohort_weights("FJ", 500, 600, 35, 480, 550, 90)
    assert result.live_weight_cohort_initial == 35
    assert result.live_weight_cohort_potential_final == 90
    assert result.live_weight_cohort_at_slaughter == 90
    assert result.live_weight_mature_stage == 500


def test_average_weights_reference_case() -> None:
    result = calc_avg_weights(100, 300, 200, 0.4)
    assert result.live_weight_cohort_final == 260
    assert result.live_weight_cohort_average == 180


def test_daily_weight_gain_reference_case() -> None:
    assert calc_daily_weight_gain(300, 100, 100) == 2
    assert calc_daily_weight_gain(100, 200, 100) == -1
