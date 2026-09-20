import pytest

from wholefarm.agroforestry import TreeBiomassStock, calculate_tree_carbon_change


def test_tree_carbon_stock_and_change() -> None:
    initial = TreeBiomassStock(10.0, 2.0, 0.47)
    final = TreeBiomassStock(14.0, 3.0, 0.47)
    change = calculate_tree_carbon_change(initial, final)

    assert initial.carbon_t == pytest.approx(12.0 * 0.47)
    assert change.change_t_c == pytest.approx((17.0 - 12.0) * 0.47)
    assert change.change_co2e_t == pytest.approx(change.change_t_c * 44.0 / 12.0)
