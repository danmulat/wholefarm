from wholefarm.gleam_demography import (
    CORE_COHORTS,
    TEN_COHORTS,
    calc_fecundity_rates,
    calc_projected_population_size,
    calc_steady_state_structure,
    calc_summary_offtake,
    calc_transition_probabilities,
)


def _core(value: float) -> dict[str, float]:
    return {cohort: value for cohort in CORE_COHORTS}


def test_fecundity_reference_case() -> None:
    result = calc_fecundity_rates(0.8, 2.0, 0.5)
    expected = 0.8 * 2.0 * 0.5 / 365.0
    assert result.fecundity_female == expected
    assert result.fecundity_male == expected


def test_transition_probabilities_have_reference_shapes() -> None:
    result = calc_transition_probabilities(_core(365.0), _core(0.1), _core(0.05))
    assert set(result.hazard_death) == set(CORE_COHORTS)
    assert set(result.probability_death) == set(TEN_COHORTS)
    assert result.probability_offtake["FC"] == 1.0
    assert result.probability_death["MC"] == 0.0


def test_steady_state_and_projected_population() -> None:
    fecundity = calc_fecundity_rates(0.8, 2.0, 0.5)
    transition = calc_transition_probabilities(_core(365.0), _core(0.1), _core(0.05))
    steady = calc_steady_state_structure(
        {"FJ": 100, "FS": 50, "FA": 30, "MJ": 100, "MS": 50, "MA": 30},
        max_simulation_years=5,
        min_lambda_change=1e-6,
        fecundity_female=fecundity.fecundity_female,
        fecundity_male=fecundity.fecundity_male,
        probability_death=transition.probability_death,
        probability_offtake=transition.probability_offtake,
        probability_growth=transition.probability_growth,
    )
    assert steady.days_to_steady_state <= 5 * 365 + 1
    assert abs(sum(steady.herd_structure.values()) - 1.0) < 1e-6
    assert abs(sum(steady.cohort_share.values()) - 1.0) < 1e-6

    projected = calc_projected_population_size(
        1000,
        fecundity.fecundity_female,
        fecundity.fecundity_male,
        transition.probability_death,
        transition.probability_offtake,
        transition.probability_growth,
        steady.growth_rate_herd,
        steady.herd_structure,
        steady.cohort_share,
    )
    assert len(projected.cohort_stock_start) == 6
    assert len(projected.cohort_offtake_heads) == 10


def test_summary_offtake_reference_shape() -> None:
    result = calc_summary_offtake(
        _core(100.0),
        _core(105.0),
        _core(102.0),
        {cohort: 0.01 for cohort in TEN_COHORTS},
        200,
    )
    assert len(result["offtake_heads"]) == 6
    assert result["stock_variation_heads"]["FJ"] == 5.0
