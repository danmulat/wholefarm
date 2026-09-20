from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_gleam_parity_manifest_is_pinned_and_nonempty() -> None:
    data = yaml.safe_load(
        (ROOT / "config" / "gleam_parity.yml").read_text(encoding="utf-8")
    )
    assert data["reference"]["commit"] == "90e416197e89093c4f3a347b263ba805d33d4aac"
    assert data["modules"]
    count = sum(len(item["functions"]) for item in data["modules"].values())
    assert count >= 50