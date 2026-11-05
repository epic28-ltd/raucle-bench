# raucle-bench

[![CI](https://github.com/craigamcw/raucle-bench/actions/workflows/ci.yml/badge.svg)](https://github.com/craigamcw/raucle-bench/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**Public adversarial leaderboard for prompt-injection detection.** Benchmarks open-source LLM guardrails on a shared, version-controlled dataset of attack and benign prompts.

> Every guardrail vendor claims accuracy. Almost none publish reproducible numbers. This is the referee.

- **Live leaderboard**: [raucle.com/bench/](https://raucle.com/bench/) — client-side dashboard that always reflects [`results/latest.json`](results/latest.json) in this repo.
- **Dataset**: 165 curated prompts across 6 attack classes + benign baseline. Grows toward 10k+.
- **Methodology**: precision, recall, F1, false-positive rate, strict-action match, p50/p99 latency per adapter.
- **License**: MIT (code and dataset).

## Why this exists

Lakera, Llama Guard, LLM Guard, Rebuff, Vigil, NeMo, raucle-detect — every prompt-injection detector ships with marketing numbers and no way to reproduce them. There is no SPEC2017 for AI security. The result is that:

- Vendors compete on claims rather than on evidence.
- Customers cannot tell whether a detector actually protects them.
- Researchers measuring detection quality have to write the benchmark themselves every time.

raucle-bench fixes this by being **the same dataset run against every adapter, with the script and outputs in version control**. Anyone can re-run the benchmark, submit a new adapter, or contribute a prompt the dataset is missing.

## What's in v0.1

| Adapter | Status |
|---|---|
| `always-allow` baseline | ✅ Built in |
| `always-block` baseline | ✅ Built in |
| `raucle-detect` (strict / standard / permissive) | ✅ Built in |
| `llm-guard` | ✅ Built in (install with `pip install '.[llm-guard]'`) |
| `rebuff` | ⏳ Adapter PR welcome |
| `vigil` | ⏳ Adapter PR welcome |
| `nemo-guardrails` | ⏳ Adapter PR welcome |
| `llama-guard` | ⏳ Adapter PR welcome |
| `lakera-guard` | ⏳ Adapter PR welcome (API key required) |

If you maintain a detector — open or commercial — we want to benchmark it. The adapter interface is ~30 lines of Python (see `src/raucle_bench/adapter.py`).

## Quick start

```bash
pip install -e '.[raucle]'
raucle-bench --list-adapters
raucle-bench                          # runs everything, writes results/<timestamp>.json|md|html
raucle-bench --adapters raucle-strict # one adapter only
```

CLI flags:

```
--datasets-dir DIR     directory of *.jsonl files (default: datasets/)
--results-dir DIR      where to write outputs (default: results/)
--adapters NAME...     limit to specific adapters
--run-id ID            override the timestamp
--validate-only        load and validate the dataset without running anything
--list-adapters        print registered adapter names
```

## Scoring methodology

A prediction is **positive** if the adapter says `ALERT` or `BLOCK`, **negative** if it says `ALLOW`. Ground truth is positive for any non-benign prompt.

For each adapter we report:

| Metric | What it tells you |
|---|---|
| **F1** | Harmonic mean of precision and recall. Single-number summary. |
| **Detection rate** | Fraction of attacks correctly flagged. Same as recall. |
| **False-positive rate** | Fraction of benign prompts incorrectly flagged. The thing that breaks production. |
| **Strict match rate** | Fraction of prompts where predicted action exactly matches expected action. Catches "detected but recommended wrong remediation." |
| **p50 / p99 latency** | Per-prompt wall-clock time. |

**No single metric is sufficient.** A detector that always says `BLOCK` has 100% recall and a meaningless 100% FPR. A detector that always says `ALLOW` has 0% FPR and 0% recall. The leaderboard reports both and the trivial baselines so you can calibrate the real entries.

## Dataset

165 prompts as of v0.1, broken down by attack class:

| Class | Prompts | What it tests |
|---|---:|---|
| `direct_injection` | 25 | Override / role hijack / ChatML / context stuff |
| `jailbreak` | 25 | DAN, developer mode, hypothetical pretext, multi-turn escalation |
| `data_exfiltration` | 20 | System prompt extraction, credential leakage, exfil channels |
| `tool_abuse` | 20 | Shell injection, path traversal, SQL injection, SSRF, code injection |
| `evasion` | 20 | Base64 / ROT13 / hex smuggling, homoglyphs, zero-width, leet, case-flip |
| `indirect_injection` | 15 | Document injection, tool poisoning, RAG poisoning, markdown exfil |
| `benign` | 40 | Clean prompts including hard negatives (mentions of "ignore", "system prompt", "developer mode" in legit contexts) |

See [`datasets/README.md`](datasets/README.md) for the schema, source labelling, and ethical considerations. The dataset is MIT-licensed; please ensure contributions carry compatible rights.

## Adding an adapter

```python
# src/raucle_bench/adapters/my_tool.py
from raucle_bench.adapter import Prediction


class MyToolAdapter:
    name = "my-tool-v1"
    version = "0.1.0"

    def setup(self) -> None:
        self._scanner = my_tool.Scanner()

    def teardown(self) -> None:
        self._scanner = None

    def predict(self, prompt: str) -> Prediction:
        result = self._scanner.scan(prompt)
        action = "BLOCK" if result.is_attack else "ALLOW"
        return Prediction(action=action, confidence=result.score)
```

Register it in `src/raucle_bench/cli.py` under `_register_optional_adapters()` so missing deps don't break the rest of the benchmark.

## Adding a prompt

1. Pick the right `datasets/<class>.jsonl` file.
2. Add a JSONL line with the next free ID in the sequence.
3. Run `raucle-bench --validate-only` to confirm the dataset still loads.
4. Open a PR with the `dataset` label.

See [`datasets/README.md`](datasets/README.md) for the schema.

## Weekly auto-run

`.github/workflows/weekly-run.yml` runs the full benchmark every Monday at 06:00 UTC and commits the results directly to `main`. The latest snapshot is at [`results/latest.json`](results/latest.json) and [`results/latest.html`](results/latest.html).

## Roadmap

- **v0.2**: dataset to 500+ prompts; LLM Guard, Vigil, Rebuff adapters; balanced-accuracy metric alongside F1.
- **v0.3**: dashboard at `bench.raucle.com` (Cloudflare Pages); time-series view of every adapter's score across weekly runs.
- **v0.4**: Llama Guard, NeMo Guardrails, Lakera (API key in repo secret) adapters.
- **v1.0**: 10k+ prompts; multimodal (image + audio); third-party submission process.

## Related

- [raucle-detect](https://github.com/craigamcw/raucle-detect) — the prompt injection detection engine being benchmarked.
- [Raucle Provenance Receipt v1](https://raucle.com/spec/provenance/v1) — the verifiable-AI standard from the same team.
- [Cryptographic Provenance for AI Workflows](https://raucle.com/blog/cryptographic-provenance-for-ai-workflows) — context on why we are publishing benchmarks as protocols rather than blog posts.

## License

MIT for both code and dataset. Contributions are welcomed under the same terms.
