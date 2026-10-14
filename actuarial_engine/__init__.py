"""Reusable actuarial development and ultimate-loss modeling engine."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .config import EngineConfig

if TYPE_CHECKING:
    from .calculation import EngineRunResult

__all__ = ["EngineConfig", "EngineRunResult", "run_modeling"]
__version__ = "0.1.0"


def __getattr__(name: str) -> Any:
    """Load runner exports lazily so ``python -m`` does not double-import them."""

    if name in {"EngineRunResult", "run_modeling"}:
        from .calculation import EngineRunResult, run_modeling

        return {"EngineRunResult": EngineRunResult, "run_modeling": run_modeling}[name]
