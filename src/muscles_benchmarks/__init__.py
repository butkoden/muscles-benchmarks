__all__ = ["run_benchmarks"]


def __getattr__(name):
    if name == "run_benchmarks":
        from .runner import run_benchmarks

        return run_benchmarks
    raise AttributeError(name)
