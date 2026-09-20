import json
from datetime import UTC, datetime

from wholefarm.provenance import (
    build_run_provenance,
    sha256_file,
    write_run_provenance,
)


def test_file_hash_is_stable(tmp_path) -> None:
    source = tmp_path / "input.csv"
    source.write_text("farm_id,value\nf1,1\n", encoding="utf-8")
    first = sha256_file(source)
    second = sha256_file(source)
    assert first == second
    assert len(first) == 64


def test_run_provenance_records_methods_and_input_hashes(tmp_path) -> None:
    source = tmp_path / "input.csv"
    source.write_text("x\n1\n", encoding="utf-8")
    provenance = build_run_provenance(
        run_id="run_001",
        model_version="0.1.0",
        git_commit="abc123",
        compliance_mode="scientific_whole_farm",
        methodology_versions={
            "GLEAM": "90e416197e89093c4f3a347b263ba805d33d4aac",
            "VM0042": "2.2",
        },
        input_paths={"farm_input": source},
        metadata={"country": "Kenya"},
        created_at=datetime(2026, 9, 20, 9, 0, tzinfo=UTC),
    )
    assert provenance.input_hashes["farm_input"] == sha256_file(source)
    assert provenance.created_at_utc == "2026-09-20T09:00:00+00:00"

    destination = write_run_provenance(provenance, tmp_path / "run.json")
    loaded = json.loads(destination.read_text(encoding="utf-8"))
    assert loaded["compliance_mode"] == "scientific_whole_farm"
    assert loaded["metadata"]["country"] == "Kenya"