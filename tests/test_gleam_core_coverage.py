import math

import pandas as pd

from wholefarm.gleam_allocation import (
    assign_allocation_shares,
    calc_cohort_to_herd_aggregation,
)
from wholefarm.gleam_energy import calc_metabolic_energy_req_eggs


def test_egg_energy_matches_pinned_gleam_placeholder() -> None:
    value = calc_metabolic_energy_req_eggs("CTL", "FA", 0.0, 0.0)
    assert math.isnan(value)


def test_cohort_to_herd_aggregation_matches_sum_rule() -> None:
    frame = pd.DataFrame(
        {
            "herd_id": ["h1", "h1", "h2"],
            "cohort": ["FA", "MA", "FA"],
            "milk_energy": [10.0, 0.0, 7.0],
            "meat_energy": [2.0, 3.0, 4.0],
        }
    )
    result = calc_cohort_to_herd_aggregation(
        frame,
        id_cols=["herd_id"],
        vars_to_sum=["milk_energy", "meat_energy"],
        cohort_short="cohort",
    )
    h1 = result.loc[result["herd_id"] == "h1"].iloc[0]
    assert h1["milk_energy"] == 10.0
    assert h1["meat_energy"] == 5.0


def test_assign_allocation_shares_applies_nonallocated_rule() -> None:
    allocation = pd.DataFrame(
        {
            "herd_id": ["h1", "h1", "h1"],
            "commodity_name": ["Milk", "Meat", "Other"],
            "allocation_share": [0.7, 0.3, 0.0],
        }
    )
    result = assign_allocation_shares(
        allocation,
        emissions_vars=["ch4_enteric", "ch4_manure_pasture"],
        commodities=["Milk", "Meat", "Other"],
        non_allocated_emission_sources=["ch4_manure_pasture"],
    )
    pasture = result[result["variable_name"] == "ch4_manure_pasture"]
    other = pasture.loc[pasture["commodity_name"] == "Other", "allocation_share"].iloc[0]
    milk = pasture.loc[pasture["commodity_name"] == "Milk", "allocation_share"].iloc[0]
    assert other == 1.0
    assert milk == 0.0

    enteric = result[result["variable_name"] == "ch4_enteric"]
    enteric_other = enteric.loc[
        enteric["commodity_name"] == "Other",
        "allocation_share",
    ].iloc[0]
    enteric_milk = enteric.loc[
        enteric["commodity_name"] == "Milk",
        "allocation_share",
    ].iloc[0]
    assert enteric_other == 0.0
    assert enteric_milk == 0.7
