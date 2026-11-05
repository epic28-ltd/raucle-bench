"""Verifies every built-in adapter satisfies the Adapter Protocol.

This test does NOT exercise adapters whose backing library isn't installed —
it just confirms the import surface is consistent so each adapter at least
fails cleanly via the runner's `setup_failed` path rather than crashing the
benchmark.
"""

from __future__ import annotations

import importlib

import pytest

from raucle_bench.adapter import Prediction

ADAPTER_MODULES = [
    "raucle_bench.adapters.baseline",
    "raucle_bench.adapters.raucle",
    "raucle_bench.adapters.llm_guard",
]


@pytest.mark.parametrize("mod_path", ADAPTER_MODULES)
def test_adapter_module_imports_or_fails_cleanly(mod_path):
    """Each adapter module must either import or raise ImportError.

    Any other exception type means the adapter has a real bug — silently
    swallowing it in the CLI's _register_optional_adapters would hide
    that bug from contributors.
    """
    import contextlib

    with contextlib.suppress(ImportError):
        importlib.import_module(mod_path)


class TestBaselinesAreUsable:
    def test_always_allow_is_an_adapter(self):
        from raucle_bench.adapters.baseline import AlwaysAllow

        a = AlwaysAllow()
        assert isinstance(a.name, str)
        assert a.name
        assert isinstance(a.version, str)
        assert a.version
        a.setup()
        result = a.predict("hi")
        a.teardown()
        assert isinstance(result, Prediction)
        assert result.action == "ALLOW"

    def test_always_block_is_an_adapter(self):
        from raucle_bench.adapters.baseline import AlwaysBlock

        a = AlwaysBlock()
        a.setup()
        assert a.predict("hi").action == "BLOCK"
        a.teardown()


class TestLLMGuardImportSurface:
    """If llm-guard is installed, exercise the adapter; otherwise skip."""

    def test_llm_guard_or_skip(self):
        pytest.importorskip("llm_guard")
        from raucle_bench.adapters.llm_guard import LLMGuardAdapter

        adapter = LLMGuardAdapter()
        # Don't actually call setup() — that downloads a multi-GB model.
        assert "llm-guard" in adapter.name

    def test_threshold_validation(self):
        pytest.importorskip("llm_guard")
        from raucle_bench.adapters.llm_guard import LLMGuardAdapter

        with pytest.raises(ValueError, match="thresholds"):
            LLMGuardAdapter(threshold=0.3, alert_threshold=0.5)
