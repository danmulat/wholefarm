"""Run provenance records for audit and MRV reproducibility."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RunProvenance:
    run_id: str
    created_at_utc: str
    model_version: str
    git_commit: str
    compliance_mode: str
    methodology_versions: dict[str, str]
    input_hashes: dict[str, str]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)


def sha256_file(path: str | Path) -> str:
    source = Path(path)
    digest = sha256()
    with source.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_input_files(paths: dict[str, str | Path]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name, path in paths.items():
        if name in hashes:
            raise ValueError(f"Duplicate input name: {name}")
        hashes[name] = sha256_file(path)
    return hashes


def build_run_provenance(
    run_id: str,
    model_version: str,
    git_commit: str,
    compliance_mode: str,
    methodology_versions: dict[str, str],
    input_paths: dict[str, str | Path] | None = None,
    metadata: dict[str, Any] | None = None,
    created_at: datetime | None = None,
) -> RunProvenance:
    if not run_id:
        raise ValueError("run_id is required")
    if not model_version:
        raise ValueError("model_version is required")
    if not git_commit:
        raise ValueError("git_commit is required")
    if not compliance_mode:
        raise ValueError("compliance_mode is required")

    timestamp = created_at or datetime.now(UTC)
    if timestamp.tzinfo is None:
        raise ValueError("created_at must be timezone aware")

    return RunProvenance(
        run_id=run_id,
        created_at_utc=timestamp.astimezone(UTC).isoformat(),
        model_version=model_version,
        git_commit=git_commit,
        compliance_mode=compliance_mode,
        methodology_versions=dict(methodology_versions),
        input_hashes=hash_input_files(input_paths or {}),
        metadata=dict(metadata or {}),
    )


def write_run_provenance(
    provenance: RunProvenance,
    path: str | Path,
) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(provenance.to_json() + "\n", encoding="utf-8")
    return destination
