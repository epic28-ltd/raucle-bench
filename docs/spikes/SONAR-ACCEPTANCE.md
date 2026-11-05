# SonarCloud accepted findings — raucle-bench

Decision owner: Craig (craigamcw/craigamcw@users.noreply.github.com).

## python:S1700 — dataclass field `prompt` (src/raucle_bench/dataset.py)

Rule: "Rename field "prompt"" — Sonar wants identifiers other than a
standard library name (`prompt` is not a builtin, but the rule targets
shadowing of builtins/module names such as `id`, `type`, etc.; in practice
S1700 flags any field/variable named after a Python builtin or a known API
symbol).

Status: **Accepted, fix rejected**.

Reason:
- `prompt` is the public, documented field name of `Prompt` (a frozen
  dataclass) and of the dataset JSONL contract: every record in
  `datasets/<class>.jsonl` requires a top-level `"prompt"` key, which
  `Prompt.from_dict` and `_validate` read by that exact name. The same
  value is passed positionally to adapter `predict(prompt)` per the
  documented Adapter Protocol in `src/raucle_bench/adapter.py`.
- Renaming the Python field (e.g. `text` or `content`) would diverge it
  from the on-disk dataset key and the Adapter Protocol vocabulary used
  across adapters, the runner, the report (leaderboard output) and the
  public docs — a breaking change for dataset authors and third-party
  adapters for zero correctness benefit.
- The field does not shadow any builtin in any reachable scope, so the
  practical risk the rule guards against does not apply here.

Handling: the field line carries `# NOSONAR` with this rationale. If the
contract ever changes (dataset schema v2), the rename should happen
together with a documented migration.
