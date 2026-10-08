import argparse
import sys
from pathlib import Path

from .domain.models import RunContext
from .features.publishing.skill import publish_saved
from .orchestration.loop import run_agent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="taskly-agent")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("--scope", choices=("pull-request", "working-tree", "gaps"), required=True)
    run.add_argument("--base")
    run.add_argument("--head")
    run.add_argument("--root", default=".")
    publish = commands.add_parser("publish")
    publish.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    root = str(Path(args.root).resolve())
    if args.command == "publish":
        print(publish_saved(Path(root)))
        return 0
    state = run_agent(
        RunContext(
            root=root,
            scope=args.scope,
            base=args.base,
            head=args.head,
            repository=None,
            pr_number=None,
            token=None,
        )
    )
    for event in state.log:
        print(f"{event.skill}: {event.summary}")
    if state.verification and not state.verification.passed:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
