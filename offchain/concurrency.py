import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Sequence, TypeVar

from offchain.logger.logging import logger

T = TypeVar("T")
U = TypeVar("U")

MAX_PROCS = (multiprocessing.cpu_count() * 2) + 1


def parallelize_with_threads(*args: Sequence[Callable]) -> Sequence[Any]:  # type: ignore[type-arg]  # noqa: E501
    """Parallelize a set of functions with a threadpool.
    Good for network calls, less for for number crunching.

    Returns:
        Sequence[Any]: sequence of results from callables
    """
    n_tasks = len(args)
    logger.debug("Starting tasks", extra={"num_tasks": n_tasks})
    with ThreadPoolExecutor(max_workers=min(n_tasks, MAX_PROCS)) as pool:
        futures = [pool.submit(fn) for fn in args]  # type: ignore[arg-type, var-annotated]  # noqa: E501
        res = [f.result() for f in futures]
    return res


def parmap(fn: Callable, args: list) -> list:
    """Run a map in parallel safely

    Args:
        fn (Callable): function to be run in parallel
        args (list): arg space to map over

    Returns:
        list: results from map calls

    Note: explicitly using a map to generate function rather than a list comprehension to prevent
        a subtle variable shadowing bug that can occur with code like this:
        >>> parallelize_with_threads(*[lambda: fn(arg) for arg in args])
    """  # noqa: E501
    return list(parallelize_with_threads(*map(lambda i: lambda: fn(i), args)))  # type: ignore[arg-type]  # noqa: E501


def batched_parmap(fn: Callable[[T], U], args: list[T], batch_size: int = 10) -> list:  # noqa: E501
    results = []
    for i in range(0, len(args), batch_size):
        batch_end = i + batch_size
        batch = args[i:batch_end]
        res = parmap(fn, batch)
        results.extend(res)
    return results
