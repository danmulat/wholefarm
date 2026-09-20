import pytest

from wholefarm.gleam_allocation import (
    AllocationShares,
    allocation_share_for_emission,
    calc_allocated_emissions,
    calc_allocation_shares,
    calc_cohort_total,
    calc_milk_allocation_energy,
)


def test_milk_allocation_energy_reference_formula() -> None:
    fpcm = 1000
    expected = (
        0.0929 * 0.04 + 0.0547 * 0.033 + 0.0395 * 0.048
    ) * 4.184 * 100 * fpcm
    assert calc_milk_allocation_energy(fpcm) == pytest.approx(expected)


def test_allocation_shares_sum_to_one() -> None:
    shares = calc_allocation_shares("CTL", 30, 50, 10, 10, 0)
    assert shares.total == pytest.approx(1.0)
    assert shares.milk == pytest.approx(0.5)


def test_pigs_allocate_all_to_meat() -> None:
    shares = calc_allocation_shares("PGS", 0, 0, 0, 0, 0)
    assert shares == AllocationShares(1, 0, 0, 0, 0)


def test_nonallocated_manure_source_goes_to_other() -> None:
    shares = AllocationShares(0.3, 0.7, 0, 0, 0)
    source = "ch4_manure_pasture"
    assert allocation_share_for_emission(source, "Other", shares) == 1
    assert allocation_share_for_emission(source, "Milk", shares) == 0


def test_allocated_emissions() -> None:
    assert calc_allocated_emissions(100, 0.3) == 30


def test_cohort_total_for_direct_emission() -> None:
    total = calc_cohort_total(
        value=0.1,
        cohort_stock_size=10,
        ration_intake=8,
        simulation_duration=365,
        variable_name="ch4_enteric",
        variable_type="Emissions",
    )
    assert total == 365


def test_cohort_total_for_feed_emission_converts_grams_to_kg() -> None:
    total = calc_cohort_total(
        value=5,
        cohort_stock_size=10,
        ration_intake=8,
        simulation_duration=365,
        variable_name="co2_ration_fertilizer",
        variable_type="Emissions",
    )
    assert total == pytest.approx(5 * 8 * 10 * 365 / 1000)
