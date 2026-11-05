"""Command-line entry point for raucle-bench."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

from raucle_bench.adapters.baseline import AlwaysAllow, AlwaysBlock
from raucle_bench.dataset import load_dataset
from raucle_bench.report import build_report, render_html, render_markdown, write_json
from raucle_bench.runner import run_adapter
from raucle_bench.scoring import score

# Registry of adapter constructors. Each value returns a fresh adapter
# instance so the runner gets a clean state.
ADAPTERS: dict[str, callable] = {
    "always-allow": AlwaysAllow,
    "always-block": AlwaysBlock,
}


def _register_optional_adapters() -> None:
    """Add adapters whose deps may not be installed. Failures are silent."""
    try:
        from raucle_bench.adapters.raucle import RaucleAdapter

        ADAPTERS["raucle-strict"] = lambda: RaucleAdapter(mode="strict")
        ADAPTERS["raucle-standard"] = lambda: RaucleAdapter(mode="standard")
        ADAPTERS["raucle-permissive"] = lambda: RaucleAdapter(mode="permissive")
    except ImportError:
        pass

    try:
        from raucle_bench.adapters.llm_guard import LLMGuardAdapter

        ADAPTERS["llm-guard"] = lambda: LLMGuardAdapter()
    except ImportError:
        pass


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="raucle-bench",
        description="Run the public adversarial leaderboard against installed adapters.",
    )
    parser.add_argument(
        "--datasets-dir",
        default="datasets",
        help="Directory containing per-class .jsonl files (default: datasets)",
    )
    parser.add_argument(
        "--results-dir",
        default="results",
        help="Where to write JSON/Markdown/HTML output (default: results)",
    )
    parser.add_argument(
        "--adapters",
        nargs="*",
        default=None,
        help="Names of adapters to run (default: all registered)",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Override the run identifier (default: ISO timestamp)",
    )
    parser.add_argument(
        "--list-adapters",
        action="store_true",
        help="Print registered adapter names and exit",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Load and validate the dataset; do not run any adapters",
    )
    return parser


def _resolve_confined_dir(raw: str, label: str) -> Path:
    """Canonicalise a CLI-supplied directory and confine it to the cwd.

    CLI arguments are LLM-controlled input in automated settings. Reject
    anything that escapes the current working directory (including via
    symlinks) instead of silently traversing elsewhere on the filesystem.
    """
    base = Path.cwd().resolve()
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = base / p
    if not base.exists():
        raise ValueError(f"{label}: working directory no longer exists")
    p = p.resolve()
    if p != base and not p.is_relative_to(base):
        raise ValueError(f"{label}: '{raw}' resolves to '{p}', outside the working directory.")
    return p


def _publish_run_id(run_id: str) -> str:
    """Restrict a CLI-supplied run id to a safe filename component."""
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", run_id):
        raise ValueError(
            f"run id '{run_id}' is not a safe filename (use up to 64 characters "
            "of letters, digits, dot, underscore, hyphen)"
        )
    return run_id


def main(argv: list[str] | None = None) -> int:
    _register_optional_adapters()
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.list_adapters:
        for name in sorted(ADAPTERS):
            print(name)
        return 0

    try:
        datasets_dir = _resolve_confined_dir(args.datasets_dir, "datasets-dir")
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Loading dataset from {datasets_dir}...", file=sys.stderr)
    try:
        prompts = load_dataset(datasets_dir)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Dataset error: {exc}", file=sys.stderr)
        return 1
    print(f"  {len(prompts)} prompts loaded.", file=sys.stderr)

    if args.validate_only:
        return 0

    adapter_names = args.adapters or sorted(ADAPTERS)
    unknown = [n for n in adapter_names if n not in ADAPTERS]
    if unknown:
        print(f"Unknown adapter(s): {unknown}", file=sys.stderr)
        print(f"Available: {sorted(ADAPTERS)}", file=sys.stderr)
        return 1

    scores = []
    for name in adapter_names:
        adapter = ADAPTERS[name]()
        print(f"Running {name}...", file=sys.stderr, end=" ", flush=True)
        result = run_adapter(adapter, prompts)
        s = score(result)
        if s.setup_failed:
            print(f"SETUP FAILED ({s.setup_failed})", file=sys.stderr)
        else:
            print(
                f"F1={s.f1:.3f} detection={s.detection_rate:.1%} "
                f"FPR={s.false_positive_rate:.1%} p50={s.latency_p50_ms:.2f}ms",
                file=sys.stderr,
            )
        scores.append(s)

    run_id = args.run_id or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    try:
        run_id = _publish_run_id(run_id)
        results_dir = _resolve_confined_dir(args.results_dir, "results-dir")
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    report = build_report(scores, prompts, run_id=run_id)

    try:
        results_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"Error creating results directory: {exc}", file=sys.stderr)
        return 1

    json_path = results_dir / f"{run_id}.json"
    md_path = results_dir / f"{run_id}.md"
    html_path = results_dir / f"{run_id}.html"
    latest_html = results_dir / "latest.html"
    latest_json = results_dir / "latest.json"

    try:
        write_json(report, json_path)
        md_path.write_text(render_markdown(report))
        html_path.write_text(render_html(report))
        # Convenience copies for the static-site deploy
        write_json(report, latest_json)
        latest_html.write_text(render_html(report))
    except OSError as exc:
        print(f"Error writing results: {exc}", file=sys.stderr)
        return 1

    print(f"\nLeaderboard written to {json_path}", file=sys.stderr)
    print(render_markdown(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
