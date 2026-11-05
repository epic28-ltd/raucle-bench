"""Dataset loader and validator for raucle-bench.

Each attack class lives in ``datasets/<class>.jsonl``. The loader parses every
line into a :class:`Prompt` and validates that required fields are present
and self-consistent.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

VALID_ATTACK_CLASSES: set[str] = {
    "direct_injection",
    "jailbreak",
    "data_exfiltration",
    "tool_abuse",
    "evasion",
    "indirect_injection",
    "benign",
}

VALID_ACTIONS: set[str] = {"ALLOW", "ALERT", "BLOCK"}
VALID_SEVERITIES: set[str] = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE"}


@dataclass(frozen=True)
class Prompt:
    """A single dataset entry."""

    id: str
    prompt: str  # NOSONAR
    category: str
    attack_class: str
    expected_action: str
    severity: str
    source: str
    notes: str = ""
    raw: dict = field(default_factory=dict, hash=False, compare=False)

    @classmethod
    def from_dict(cls, d: dict) -> Prompt:
        return cls(
            id=d["id"],
            prompt=d["prompt"],
            category=d["category"],
            attack_class=d["attack_class"],
            expected_action=d["expected_action"],
            severity=d["severity"],
            source=d["source"],
            notes=d.get("notes", ""),
            raw=d,
        )

    @property
    def is_malicious(self) -> bool:
        """True for any non-benign prompt regardless of expected action."""
        return self.attack_class != "benign"


def load_dataset(datasets_dir: str | Path) -> list[Prompt]:
    """Load every ``*.jsonl`` file in *datasets_dir* and return one list.

    Order is sorted by file name then file order so runs are reproducible.
    """
    datasets_dir = Path(datasets_dir)
    if not datasets_dir.is_dir():
        raise FileNotFoundError(f"Dataset directory not found: {datasets_dir}")

    prompts: list[Prompt] = []
    seen_ids: set[str] = set()

    for jsonl_path in sorted(datasets_dir.glob("*.jsonl")):
        for line_no, line in enumerate(_read_lines(jsonl_path), start=1):
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{jsonl_path.name}:{line_no}: invalid JSON: {exc}") from exc

            _validate(obj, where=f"{jsonl_path.name}:{line_no}")

            if obj["id"] in seen_ids:
                raise ValueError(f"{jsonl_path.name}:{line_no}: duplicate id {obj['id']!r}")
            seen_ids.add(obj["id"])

            prompts.append(Prompt.from_dict(obj))

    return prompts


def _read_lines(path: Path) -> Iterable[str]:
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if stripped:
                yield stripped


def _validate(obj: dict, *, where: str) -> None:
    required = {"id", "prompt", "category", "attack_class", "expected_action", "severity", "source"}
    missing = required - obj.keys()
    if missing:
        raise ValueError(f"{where}: missing fields {sorted(missing)}")

    if obj["attack_class"] not in VALID_ATTACK_CLASSES:
        raise ValueError(
            f"{where}: attack_class {obj['attack_class']!r} not in {sorted(VALID_ATTACK_CLASSES)}"
        )
    if obj["expected_action"] not in VALID_ACTIONS:
        raise ValueError(
            f"{where}: expected_action {obj['expected_action']!r} not in {sorted(VALID_ACTIONS)}"
        )
    if obj["severity"] not in VALID_SEVERITIES:
        raise ValueError(f"{where}: severity {obj['severity']!r} not in {sorted(VALID_SEVERITIES)}")

    # Benign prompts must expect ALLOW with severity NONE; attacks the opposite.
    if obj["attack_class"] == "benign":
        if obj["expected_action"] != "ALLOW":
            raise ValueError(f"{where}: benign prompt must expect_action=ALLOW")
        if obj["severity"] != "NONE":
            raise ValueError(f"{where}: benign prompt must have severity=NONE")
    else:
        if obj["expected_action"] == "ALLOW":
            raise ValueError(f"{where}: attack must not expect_action=ALLOW")
        if obj["severity"] == "NONE":
            raise ValueError(f"{where}: attack must not have severity=NONE")


def summarise(prompts: list[Prompt]) -> dict[str, int]:
    """Return a compact summary suitable for the leaderboard header."""
    summary: dict[str, int] = {"total": len(prompts)}
    by_class: dict[str, int] = {}
    for p in prompts:
        by_class[p.attack_class] = by_class.get(p.attack_class, 0) + 1
    summary["by_attack_class"] = by_class  # type: ignore[assignment]
    return summary
