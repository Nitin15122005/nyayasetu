# -*- coding: utf-8 -*-
"""
evaluation/runners/registry.py — suite name -> evaluator class

A plain dict + decorator, not a metaclass or plugin-discovery system —
there are 15 evaluators, all living in this one package, so anything
fancier would be solving a problem this framework doesn't have. If
evaluation/ ever needs externally-pluggable evaluators (e.g. a separate
package contributing a new suite), swap this for entry_points-based
discovery then, not preemptively now.
"""

from __future__ import annotations

from typing import Type

EVALUATOR_REGISTRY: dict[str, Type] = {}


def register(suite_name: str):
    def decorator(cls):
        if suite_name in EVALUATOR_REGISTRY and EVALUATOR_REGISTRY[suite_name] is not cls:
            raise ValueError(f"Suite '{suite_name}' is already registered to "
                              f"{EVALUATOR_REGISTRY[suite_name].__name__}")
        EVALUATOR_REGISTRY[suite_name] = cls
        cls.suite = suite_name
        return cls
    return decorator


def get_evaluator_class(suite: str):
    if not EVALUATOR_REGISTRY:
        import evaluation.runners  # noqa: F401  triggers registration
    if suite not in EVALUATOR_REGISTRY:
        raise KeyError(f"No evaluator registered for suite '{suite}'. "
                        f"Registered: {sorted(EVALUATOR_REGISTRY)}")
    return EVALUATOR_REGISTRY[suite]


def list_registered_suites() -> list[str]:
    if not EVALUATOR_REGISTRY:
        import evaluation.runners  # noqa: F401
    return sorted(EVALUATOR_REGISTRY)
