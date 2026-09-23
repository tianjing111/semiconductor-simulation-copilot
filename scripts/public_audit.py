#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


FORBIDDEN_TEXT = (
    "/" + "home" + "/",
    "/" + "usr" + "/" + "syn" + "opsys",
    "vnc" + "user",
    "S-" + "Litho",
    "LM_" + "LICENSE",
    "baseline_" + "nominal_thickness",
)
FORBIDDEN_SUFFIXES = {"." + value for value in ("slo", "gds", "npz", "pt", "pth", "ckpt")}
SKIP_PARTS = {".git", "__pycache__", ".pytest_cache"}
MAX_FILE_BYTES = 10 * 1024 * 1024


def audit(root: Path) -> list[str]:
    issues = []
    for path in root.rglob("*"):
        if not path.is_file() or any(part in SKIP_PARTS for part in path.parts):
            continue
        relative = path.relative_to(root)
        size = path.stat().st_size
        if size > MAX_FILE_BYTES:
            issues.append(f"large_file:{relative}:{size}")
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            issues.append(f"forbidden_suffix:{relative}")
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".ico"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in FORBIDDEN_TEXT:
            if pattern.lower() in text.lower():
                issues.append(f"forbidden_text:{relative}:{pattern}")
    return issues


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit the repository for public-release blockers")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    issues = audit(args.root.resolve())
    if issues:
        print("PUBLIC_AUDIT_FAILED")
        for issue in issues:
            print(issue)
        raise SystemExit(1)
    print("PUBLIC_AUDIT_PASS")


if __name__ == "__main__":
    main()

