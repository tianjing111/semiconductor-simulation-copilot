from __future__ import annotations

import argparse
import json
from pathlib import Path

from .build_assets import build
from .service import CopilotService


def main() -> None:
    parser = argparse.ArgumentParser(description="Semiconductor simulation copilot utilities")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("build-assets")
    diagnose = subparsers.add_parser("diagnose")
    diagnose.add_argument("log", type=Path)
    search = subparsers.add_parser("search")
    search.add_argument("query")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command == "build-assets":
        result = build(root)
    else:
        service = CopilotService(root)
        result = service.diagnose(args.log.read_text(encoding="utf-8", errors="replace")) if args.command == "diagnose" else {"results": service.search(args.query)}
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()

