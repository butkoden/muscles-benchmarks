from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .runner import run_benchmarks


__all__ = ["run_benchmarks"]


def __getattr__(name):
    if name == "run_benchmarks":
        from .runner import run_benchmarks

        return run_benchmarks
    raise AttributeError(name)
