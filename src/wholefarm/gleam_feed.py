"""Feed ration emission factor weighting from the pinned FAO GLEAM source."""

from __future__ import annotations

from .gleam_core import _fraction, _nonnegative


def _weighted(feed_ration_fraction: float, emission_factor: float | None) -> float | None:
    _fraction(feed_ration_fraction, "feed_ration_fraction")
    if emission_factor is None:
        return None
    _nonnegative(emission_factor, "emission_factor")
    return feed_ration_fraction * emission_factor


def calc_co2_ration_fertilizer(feed_ration_fraction: float, factor: float | None) -> float | None:
    return _weighted(feed_ration_fraction, factor)


def calc_co2_ration_pesticides(feed_ration_fraction: float, factor: float | None) -> float | None:
    return _weighted(feed_ration_fraction, factor)


def calc_co2_ration_crop_activities(feed_ration_fraction: float, factor: float | None) -> float | None:
    return _weighted(feed_ration_fraction, factor)


def calc_co2_ration_luc_nopeat(feed_ration_fraction: float, factor: float | None) -> float | None:
    return _weighted(feed_ration_fraction, factor)


def calc_co2_ration_luc_peat(feed_ration_fraction: float, factor: float | None) -> float | None:
    return _weighted(feed_ration_fraction, factor)


def calc_n2o_ration_fertilizer(feed_ration_fraction: float, factor: float | None) -> float | None:
    return _weighted(feed_ration_fraction, factor)


def calc_n2o_ration_manure(feed_ration_fraction: float, factor: float | None) -> float | None:
    return _weighted(feed_ration_fraction, factor)


def calc_n2o_ration_crop_residues(feed_ration_fraction: float, factor: float | None) -> float | None:
    return _weighted(feed_ration_fraction, factor)


def calc_ch4_ration_rice(feed_ration_fraction: float, factor: float | None) -> float | None:
    return _weighted(feed_ration_fraction, factor)


def aggregate_ration_components(values: list[float | None]) -> float | None:
    finite = [value for value in values if value is not None]
    if not finite:
        return None
    return float(sum(finite))
