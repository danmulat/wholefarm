"""Cohort level GLEAM calculation chain using the pinned core equations.

The chain connects energy demand, dry matter intake, nitrogen balance, enteric
methane, manure methane, manure nitrous oxide, and animal production for one
species and sex age cohort. Inputs remain explicit so missing farm data are not
silently replaced with unrelated defaults.
"""

from __future__ import annotations

from dataclasses import dataclass

from .gleam_core import (
    GLEAM_MILK_PRODUCERS,
    ManureManagementSystem,
    MeatProduction,
    MilkProduction,
    calc_ch4_enteric,
    calc_ch4_manure,
    calc_conversion_factor_ym,
    calc_fibre_production,
    calc_meat_production,
    calc_milk_production,
    calc_n2o_manure_direct,
    calc_n2o_manure_leaching,
    calc_n2o_manure_total,
    calc_n2o_manure_volatilization,
    calc_nitrogen_excretion,
    calc_nitrogen_intake,
    calc_nitrogen_retention,
    calc_volatile_solids,
)
from .gleam_energy import (
    calc_metabolic_energy_req_activity,
    calc_metabolic_energy_req_fibre,
    calc_metabolic_energy_req_growth,
    calc_metabolic_energy_req_lactation,
    calc_metabolic_energy_req_maintenance,
    calc_metabolic_energy_req_pregnancy,
    calc_metabolic_energy_req_work,
    calc_ration_intake,
    calc_reg_growth,
    calc_rem_maintenance,
    calc_total_metabolic_energy_req,
)


@dataclass(frozen=True)
class RationProfile:
    digestibility_fraction: float
    gross_energy_mj_kg_dm: float
    metabolizable_energy_mj_kg_dm: float
    nitrogen_kg_kg_dm: float
    urinary_energy_fraction: float
    ash_fraction: float

    def __post_init__(self) -> None:
        for value, name in (
            (self.digestibility_fraction, "digestibility_fraction"),
            (self.urinary_energy_fraction, "urinary_energy_fraction"),
            (self.ash_fraction, "ash_fraction"),
        ):
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between zero and one")
        if self.gross_energy_mj_kg_dm <= 0:
            raise ValueError("gross_energy_mj_kg_dm must be positive")
        if self.metabolizable_energy_mj_kg_dm <= 0:
            raise ValueError("metabolizable_energy_mj_kg_dm must be positive")
        if self.nitrogen_kg_kg_dm < 0:
            raise ValueError("nitrogen_kg_kg_dm must be nonnegative")


@dataclass(frozen=True)
class CohortInputs:
    species_short: str
    cohort_short: str
    cohort_stock_size: float
    simulation_duration_days: float
    live_weight_cohort_average: float
    live_weight_cohort_initial: float
    live_weight_cohort_final: float
    live_weight_mature_stage: float
    live_weight_cohort_at_slaughter: float
    cohort_duration_days: float
    offtake_rate: float
    offtake_heads_assessment: float = 0.0
    low_activity_fraction: float = 0.0
    high_activity_fraction: float = 0.0
    age_first_parturition: float | None = None
    lactating_females_fraction: float = 0.0
    milk_yield_day: float = 0.0
    milk_protein_fraction: float = 0.033
    milk_fat_fraction: float = 0.04
    milk_lactose_fraction: float = 0.048
    fibre_yield_year: float = 0.0
    litter_size: float = 1.0
    parturition_rate: float = 0.0
    live_weight_at_birth: float = 0.0
    live_weight_at_weaning: float = 0.0
    pregnancy_duration: float = 0.0
    non_productive_duration: float = 0.0
    lactation_duration: float = 0.0
    death_rate_juvenile: float = 0.0
    draught_work_hours_female: float = 0.0
    draught_work_hours_male: float = 0.0
    draught_fraction_female: float = 0.0
    draught_fraction_male: float = 0.0
    ch4_mitigation_factor: float = 1.0
    carcass_dressing_fraction: float = 0.5
    bone_free_meat_fraction: float = 0.75
    meat_protein_fraction: float = 0.2


@dataclass(frozen=True)
class CohortEnergyResult:
    maintenance_mj_head_day: float
    activity_mj_head_day: float
    growth_mj_head_day: float
    lactation_mj_head_day: float
    work_mj_head_day: float
    fibre_mj_head_day: float
    pregnancy_mj_head_day: float
    total_mj_head_day: float


@dataclass(frozen=True)
class CohortNitrogenResult:
    intake_kg_n_head_day: float
    retention_kg_n_head_day: float
    excretion_kg_n_head_day: float


@dataclass(frozen=True)
class CohortEmissionResult:
    ym_percent: float
    enteric_ch4_kg_head_day: float
    volatile_solids_kg_head_day: float
    manure_ch4_kg_head_day: dict[str, float]
    manure_n2o_kg_head_day: dict[str, float]


@dataclass(frozen=True)
class CohortProductionResult:
    milk: MilkProduction
    meat: MeatProduction
    fibre_kg: float


@dataclass(frozen=True)
class CohortTotals:
    enteric_ch4_kg: float
    manure_ch4_kg: float
    manure_n2o_kg: float
    nitrogen_intake_kg: float
    nitrogen_excretion_kg: float


@dataclass(frozen=True)
class GleamCohortResult:
    ration_intake_kg_dm_head_day: float
    energy: CohortEnergyResult
    nitrogen: CohortNitrogenResult
    emissions: CohortEmissionResult
    production: CohortProductionResult
    totals: CohortTotals


def _total_manure_ch4(values: dict[str, float]) -> float:
    return (
        values["ch4_manure_pasture"]
        + values["ch4_manure_burned"]
        + values["ch4_manure_other"]
    )


def _total_manure_n2o(values: dict[str, float]) -> float:
    return (
        values["n2o_manure_pasture_total"]
        + values["n2o_manure_burned_total"]
        + values["n2o_manure_other_total"]
    )


def run_gleam_cohort(
    inputs: CohortInputs,
    ration: RationProfile,
    manure_systems: dict[str, ManureManagementSystem],
) -> GleamCohortResult:
    """Run the connected calculation chain for one GLEAM cohort."""

    maintenance = calc_metabolic_energy_req_maintenance(
        inputs.species_short,
        inputs.cohort_short,
        inputs.live_weight_cohort_average,
        lactating_females_fraction=inputs.lactating_females_fraction,
        offtake_rate=inputs.offtake_rate,
        age_first_parturition=inputs.age_first_parturition,
    )
    activity = calc_metabolic_energy_req_activity(
        inputs.species_short,
        inputs.cohort_short,
        maintenance,
        inputs.live_weight_cohort_average,
        inputs.low_activity_fraction,
        inputs.high_activity_fraction,
    )
    daily_weight_gain = (
        inputs.live_weight_cohort_final - inputs.live_weight_cohort_initial
    ) / inputs.cohort_duration_days
    growth = calc_metabolic_energy_req_growth(
        inputs.species_short,
        inputs.cohort_short,
        live_weight_cohort_average=inputs.live_weight_cohort_average,
        live_weight_cohort_final=inputs.live_weight_cohort_final,
        live_weight_cohort_initial=inputs.live_weight_cohort_initial,
        live_weight_mature_stage=inputs.live_weight_mature_stage,
        daily_weight_gain=max(daily_weight_gain, 0.0),
        offtake_rate=inputs.offtake_rate,
        cohort_duration_days=inputs.cohort_duration_days,
    )
    lactation = calc_metabolic_energy_req_lactation(
        inputs.species_short,
        inputs.cohort_short,
        lactating_females_fraction=inputs.lactating_females_fraction,
        milk_yield_day=inputs.milk_yield_day,
        milk_fat_fraction=inputs.milk_fat_fraction,
        non_productive_duration=inputs.non_productive_duration,
        pregnancy_duration=inputs.pregnancy_duration,
        litter_size=inputs.litter_size,
        death_rate_juvenile=inputs.death_rate_juvenile,
        live_weight_at_birth=inputs.live_weight_at_birth,
        live_weight_at_weaning=inputs.live_weight_at_weaning,
        lactation_duration=inputs.lactation_duration,
        parturition_rate=inputs.parturition_rate,
    )
    work = calc_metabolic_energy_req_work(
        inputs.species_short,
        inputs.cohort_short,
        maintenance,
        inputs.draught_work_hours_female,
        inputs.draught_work_hours_male,
        inputs.draught_fraction_female,
        inputs.draught_fraction_male,
    )
    fibre = calc_metabolic_energy_req_fibre(
        inputs.species_short,
        inputs.cohort_short,
        inputs.fibre_yield_year,
    )
    pregnancy = calc_metabolic_energy_req_pregnancy(
        inputs.species_short,
        inputs.cohort_short,
        metabolic_energy_req_maintenance=maintenance,
        parturition_rate=inputs.parturition_rate,
        litter_size=inputs.litter_size,
        pregnancy_duration=inputs.pregnancy_duration,
        non_productive_duration=inputs.non_productive_duration,
        lactation_duration=inputs.lactation_duration,
        cohort_duration_days=inputs.cohort_duration_days,
        offtake_rate=inputs.offtake_rate,
    )

    rem = calc_rem_maintenance(inputs.species_short, ration.digestibility_fraction)
    reg = calc_reg_growth(inputs.species_short, ration.digestibility_fraction)
    total_energy = calc_total_metabolic_energy_req(
        inputs.species_short,
        maintenance,
        activity,
        lactation,
        work,
        pregnancy,
        rem,
        growth,
        fibre,
        0.0,
        reg,
        ration.digestibility_fraction,
    )
    ration_intake = calc_ration_intake(
        inputs.species_short,
        total_energy,
        ration.gross_energy_mj_kg_dm,
        ration.metabolizable_energy_mj_kg_dm,
    )

    nitrogen_intake = calc_nitrogen_intake(
        ration_intake,
        ration.nitrogen_kg_kg_dm,
    )
    nitrogen_retention = calc_nitrogen_retention(
        inputs.species_short,
        inputs.cohort_short,
        milk_protein_fraction=inputs.milk_protein_fraction,
        milk_yield_day=inputs.milk_yield_day,
        daily_weight_gain=max(daily_weight_gain, 0.0),
        fibre_yield_year=inputs.fibre_yield_year,
        litter_size=inputs.litter_size,
        parturition_rate=inputs.parturition_rate,
        live_weight_at_weaning=inputs.live_weight_at_weaning,
        live_weight_at_birth=inputs.live_weight_at_birth,
        pregnancy_duration=inputs.pregnancy_duration,
        cohort_duration_days=inputs.cohort_duration_days,
    )
    nitrogen_excretion = calc_nitrogen_excretion(
        inputs.species_short,
        nitrogen_intake,
        nitrogen_retention,
    )

    ym = calc_conversion_factor_ym(
        inputs.species_short,
        inputs.cohort_short,
        ration.digestibility_fraction,
    )
    enteric = calc_ch4_enteric(
        inputs.species_short,
        ym,
        inputs.ch4_mitigation_factor,
        ration.gross_energy_mj_kg_dm,
        ration_intake,
    )
    volatile_solids = calc_volatile_solids(
        ration_intake,
        ration.digestibility_fraction,
        ration.urinary_energy_fraction,
        ration.ash_fraction,
    )
    manure_ch4 = calc_ch4_manure(volatile_solids, manure_systems)
    manure_direct = calc_n2o_manure_direct(nitrogen_excretion, manure_systems)
    manure_vol = calc_n2o_manure_volatilization(
        nitrogen_excretion,
        manure_systems,
    )
    manure_leach = calc_n2o_manure_leaching(
        nitrogen_excretion,
        manure_systems,
    )
    manure_n2o = calc_n2o_manure_total(
        manure_vol["n2o_manure_pasture_vol"],
        manure_leach["n2o_manure_pasture_leach"],
        manure_vol["n2o_manure_burned_vol"],
        manure_leach["n2o_manure_burned_leach"],
        manure_vol["n2o_manure_other_vol"],
        manure_leach["n2o_manure_other_leach"],
        manure_direct["n2o_manure_pasture_direct"],
        manure_direct["n2o_manure_burned_direct"],
        manure_direct["n2o_manure_other_direct"],
    )

    if (
        inputs.species_short in GLEAM_MILK_PRODUCERS
        and inputs.cohort_short == "FA"
    ):
        milk = calc_milk_production(
            inputs.species_short,
            inputs.cohort_short,
            inputs.milk_yield_day,
            inputs.simulation_duration_days,
            inputs.cohort_stock_size,
            inputs.lactating_females_fraction,
            inputs.milk_protein_fraction,
            inputs.milk_fat_fraction,
            inputs.milk_lactose_fraction,
        )
    else:
        milk = MilkProduction(0.0, 0.0, 0.0)

    meat = calc_meat_production(
        inputs.offtake_heads_assessment,
        inputs.live_weight_cohort_at_slaughter,
        inputs.carcass_dressing_fraction,
        inputs.bone_free_meat_fraction,
        inputs.meat_protein_fraction,
    )
    fibre_production = calc_fibre_production(
        inputs.species_short,
        inputs.cohort_short,
        inputs.fibre_yield_year,
        inputs.simulation_duration_days,
        inputs.cohort_stock_size,
    )

    exposure = inputs.cohort_stock_size * inputs.simulation_duration_days
    totals = CohortTotals(
        enteric_ch4_kg=enteric * exposure,
        manure_ch4_kg=_total_manure_ch4(manure_ch4) * exposure,
        manure_n2o_kg=_total_manure_n2o(manure_n2o) * exposure,
        nitrogen_intake_kg=nitrogen_intake * exposure,
        nitrogen_excretion_kg=nitrogen_excretion * exposure,
    )

    return GleamCohortResult(
        ration_intake_kg_dm_head_day=ration_intake,
        energy=CohortEnergyResult(
            maintenance,
            activity,
            growth,
            lactation,
            work,
            fibre,
            pregnancy,
            total_energy,
        ),
        nitrogen=CohortNitrogenResult(
            nitrogen_intake,
            nitrogen_retention,
            nitrogen_excretion,
        ),
        emissions=CohortEmissionResult(
            ym,
            enteric,
            volatile_solids,
            manure_ch4,
            manure_n2o,
        ),
        production=CohortProductionResult(
            milk,
            meat,
            fibre_production,
        ),
        totals=totals,
    )
