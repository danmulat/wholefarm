"""Check that the pinned GLEAM core function surface exists in Python."""

from __future__ import annotations

import importlib
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config" / "gleam_parity.yml"


def main() -> None:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    missing: list[str] = []
    for module_name, module_info in data["modules"].items():
        module = importlib.import_module(f"wholefarm.{module_name}")
        for function_name in module_info["functions"]:
            if not callable(getattr(module, function_name, None)):
                missing.append(f"{module_name}.{function_name}")
    if missing:
        formatted = "\n".join(missing)
        raise SystemExit(f"Missing pinned GLEAM functions:\n{formatted}")
    count = sum(len(item["functions"]) for item in data["modules"].values())
    print(f"GLEAM function coverage check passed for {count} functions")


if __name__ == "__main__":
    main()
