import numpy as np

from wholefarm.soc_spiking import SpikingMasks, build_spiking_folds


def test_spiking_folds_validate_only_on_target_and_remove_overlapping_groups() -> None:
    groups = np.asarray(
        [
            "g1", "g2", "g3", "g4", "g5",
            "g1", "g2", "g6",
            "g3", "g7", "g8",
        ],
        dtype=object,
    )
    masks = SpikingMasks(
        target=np.asarray([1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0], dtype=bool),
        compatible_legacy=np.asarray(
            [0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0],
            dtype=bool,
        ),
        broader_legacy=np.asarray(
            [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1],
            dtype=bool,
        ),
    )
    nodes = build_spiking_folds(groups, masks, outer_cv=5)

    assert set(nodes) == {
        "target_only",
        "target_plus_compatible",
        "target_plus_all_legacy",
    }
    assert len(nodes["target_only"]) == 5

    for node_folds in nodes.values():
        for fold in node_folds:
            assert all(index < 5 for index in fold.test_indices)
            assert not any(
                str(groups[index]) in set(fold.held_out_groups)
                for index in fold.train_indices
            )


def test_compatible_node_does_not_include_broader_legacy() -> None:
    groups = np.asarray(["g1", "g2", "g3", "g4", "g5", "g6", "g7"], dtype=object)
    masks = SpikingMasks(
        target=np.asarray([1, 1, 1, 1, 1, 0, 0], dtype=bool),
        compatible_legacy=np.asarray([0, 0, 0, 0, 0, 1, 0], dtype=bool),
        broader_legacy=np.asarray([0, 0, 0, 0, 0, 0, 1], dtype=bool),
    )
    nodes = build_spiking_folds(groups, masks, outer_cv=5)
    for fold in nodes["target_plus_compatible"]:
        assert 6 not in fold.train_indices
