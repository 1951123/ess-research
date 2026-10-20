"""One public command for archive-first AreCEL preparation and consumption."""

import argparse
import json
import os
import subprocess
import sys

from .archive import DATASETS, prepare


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    command = sub.add_parser("prepare")
    command.add_argument("--issue", type=int, required=True)
    command.add_argument("--dataset", choices=DATASETS, required=True)
    command.add_argument("--keep-scratch", action="store_true")
    command.add_argument(
        "consumer",
        nargs=argparse.REMAINDER,
        help="-- COMMAND [ARGS...] runs before cleanup",
    )
    args = parser.parse_args(argv)
    consumer = args.consumer
    if consumer[:1] == ["--"]:
        consumer = consumer[1:]
    if not consumer and not args.keep_scratch:
        parser.error(
            "provide a consuming command after --, or explicitly use --keep-scratch"
        )
    try:
        with prepare(
            issue=args.issue, dataset=args.dataset, keep_scratch=args.keep_scratch
        ) as prepared:
            print(
                json.dumps(
                    {
                        "run_root": str(prepared.run_root),
                        "dataset_root": str(prepared.dataset_root),
                        "splits": prepared.manifest["splits"],
                    }
                ),
                flush=True,
            )
            if consumer:
                env = dict(
                    os.environ,
                    ESS_ISSUE_ROOT=str(prepared.run_root),
                    ESS_ARECEL_DATASET_ROOT=str(prepared.dataset_root),
                )
                subprocess.run(consumer, env=env, check=True)
    except Exception as exc:
        print(f"AreCEL preparation failed: {exc}", file=sys.stderr)
        for note in getattr(exc, "__notes__", []):
            print(note, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
