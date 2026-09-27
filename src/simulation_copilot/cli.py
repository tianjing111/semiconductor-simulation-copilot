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
    search.add_argument("--mode", choices=("keyword", "tfidf", "hybrid"), default="hybrid")
    ask = subparsers.add_parser("ask")
    ask.add_argument("question")
    ask.add_argument("--mode", choices=("keyword", "tfidf", "hybrid"), default="hybrid")
    agent = subparsers.add_parser("agent")
    agent.add_argument("request")
    agent.add_argument("--config", type=Path)
    agent.add_argument("--run-id", default="")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command == "build-assets":
        result = build(root)
    else:
        service = CopilotService(root)
        if args.command == "diagnose":
            result = service.diagnose(args.log.read_text(encoding="utf-8", errors="replace"))
        elif args.command == "ask":
            result = service.ask(args.question, args.mode)
        elif args.command == "agent":
            context = {"run_id": args.run_id}
            if args.config:
                context["config"] = json.loads(args.config.read_text(encoding="utf-8"))
            result = service.agent_request(args.request, context)
        else:
            result = {"results": service.search(args.query, mode=args.mode)}
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
