"""Archive-first AreCEL API; imports do not inspect machine configuration."""

__all__ = ["PreparedDataset", "PreparationError", "prepare"]


def __getattr__(name: str):
    if name in __all__:
        from . import archive

        value = getattr(archive, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
