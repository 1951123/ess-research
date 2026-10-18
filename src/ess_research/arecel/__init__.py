"""Audited AreCEL dataset-boundary utilities.

The public helpers are loaded lazily so ``python -m
ess_research.arecel.forest10`` does not import the module before ``runpy``
executes it.
"""

__all__ = [
    "InputContractError",
    "adapt_query_sql",
    "build_artifacts",
    "inspect_source",
    "validate_source",
]


def __getattr__(name: str):
    if name in __all__:
        from . import forest10

        return getattr(forest10, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
