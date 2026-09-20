"""Domain compatible data spiking folds for digital SOC validation.

The fold construction follows the reference principle used in the pinned Florida
workflow. Outer validation is always performed on the local target observations.
Additional compatible or broader legacy records may enter training, but any
record sharing a held out spatial group is removed from that fold.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.model_selection import GroupKFold


@dataclass(frozen=True)
class SpikingFold:
    node: str
    fold: int
    train_indices: tuple[int, ...]
    test_indices: tuple[int, ...]
    held_out_groups: tuple[str, ...]


@dataclass(frozen=True)
class SpikingMasks:
    target: np.ndarray
    compatible_legacy: np.ndarray
    broader_legacy: np.ndarray

    def __post_init__(self) -> None:
        arrays = (
            np.asarray(self.target, dtype=bool),
            np.asarray(self.compatible_legacy, dtype=bool),
            np.asarray(self.broader_legacy, dtype=bool),
        )
        lengths = {len(item) for item in arrays}
        if len(lengths) != 1:
            raise ValueError("All spiking masks must have equal lengths")
        if np.any(arrays[0] & arrays[1]) or np.any(arrays[0] & arrays[2]):
            raise ValueError("Target observations must not also be marked as legacy")
        if np.any(arrays[1] & arrays[2]):
            raise ValueError("Compatible and broader legacy masks must be disjoint")


def build_spiking_folds(
    spatial_groups: np.ndarray,
    masks: SpikingMasks,
    outer_cv: int = 5,
) -> dict[str, tuple[SpikingFold, ...]]:
    groups = np.asarray(spatial_groups, dtype=object)
    target_mask = np.asarray(masks.target, dtype=bool)
    compatible_mask = np.asarray(masks.compatible_legacy, dtype=bool)
    broader_mask = np.asarray(masks.broader_legacy, dtype=bool)

    if len(groups) != len(target_mask):
        raise ValueError("spatial_groups length must equal spiking mask length")
    target_indices = np.flatnonzero(target_mask)
    if len(target_indices) < 2:
        raise ValueError("At least two target observations are required")

    target_groups = groups[target_indices]
    unique_target_groups = len(set(str(value) for value in target_groups))
    splits = min(outer_cv, unique_target_groups)
    if splits < 2:
        raise ValueError("At least two target spatial groups are required")

    nodes: dict[str, list[SpikingFold]] = {
        "target_only": [],
        "target_plus_compatible": [],
        "target_plus_all_legacy": [],
    }
    splitter = GroupKFold(n_splits=splits)

    for fold, (target_train_local, target_test_local) in enumerate(
        splitter.split(target_indices, groups=target_groups),
        start=1,
    ):
        target_train = target_indices[target_train_local]
        target_test = target_indices[target_test_local]
        held_out = {str(value) for value in groups[target_test]}

        allowed = np.asarray(
            [str(value) not in held_out for value in groups],
            dtype=bool,
        )
        compatible_indices = np.flatnonzero(compatible_mask & allowed)
        broader_indices = np.flatnonzero(broader_mask & allowed)

        node_indices = {
            "target_only": np.asarray(target_train, dtype=int),
            "target_plus_compatible": np.unique(
                np.concatenate([target_train, compatible_indices])
            ),
            "target_plus_all_legacy": np.unique(
                np.concatenate([target_train, compatible_indices, broader_indices])
            ),
        }

        for node, train_indices in node_indices.items():
            if any(str(groups[index]) in held_out for index in train_indices):
                raise RuntimeError("Training data overlap a held out spatial group")
            nodes[node].append(
                SpikingFold(
                    node=node,
                    fold=fold,
                    train_indices=tuple(int(value) for value in train_indices),
                    test_indices=tuple(int(value) for value in target_test),
                    held_out_groups=tuple(sorted(held_out)),
                )
            )

    return {name: tuple(values) for name, values in nodes.items()}
