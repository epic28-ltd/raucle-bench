"""Baseline adapters — calibration references, not real detectors.

These exist so the leaderboard always has at least two data points and the
F1 / FPR numbers can be sanity-checked against trivial baselines:

* ``always_allow`` mimics a system with no guardrails. Catches no attacks
  but has perfect false-positive rate. Sets the floor.
* ``always_block`` blocks everything. Catches every attack but blocks
  every benign prompt too. Sets the precision ceiling on attacks and the
  precision floor on benign.

A real detector must beat both on a balanced metric (F1 or balanced
accuracy) to be useful.
"""

from __future__ import annotations

from raucle_bench.adapter import Prediction


class AlwaysAllow:
    name = "always-allow-baseline"
    version = "1.0.0"

    def predict(self, _prompt: str) -> Prediction:
        # _prompt is unused by design: baseline ignores input text.
        return Prediction(action="ALLOW", confidence=0.0, detail="no-op baseline")

    def setup(self) -> None:
        # No-op: this baseline holds no state, nothing to initialise.
        pass

    def teardown(self) -> None:
        # No-op: fixture-less baseline has nothing to clean up.
        pass


class AlwaysBlock:
    name = "always-block-baseline"
    version = "1.0.0"

    def predict(self, _prompt: str) -> Prediction:
        # _prompt is unused by design: baseline blocks every prompt.
        return Prediction(action="BLOCK", confidence=1.0, detail="no-op baseline")

    def setup(self) -> None:
        # No-op: this baseline holds no state, nothing to initialise.
        pass

    def teardown(self) -> None:
        # No-op: fixture-less baseline has nothing to clean up.
        pass
