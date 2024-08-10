import asyncio
import time

import pytest

from offchain.utils.utils import safe_async_runner, parse_content_type


def build_coro(ret_val: int, delay: float):  # type: ignore[no-untyped-def]
    async def coro():  # type: ignore[no-untyped-def]
        await asyncio.sleep(delay)
        return ret_val

    return coro


@pytest.mark.asyncio
async def test_secure_gather_runner_happy_path():  # type: ignore[no-untyped-def]
    results = await asyncio.gather(*[safe_async_runner()(build_coro(ret_val, delay=0.1))() for ret_val in range(10)])
    assert results == list(range(10))


@pytest.mark.asyncio
async def test_secure_gather_runner_timeout():  # type: ignore[no-untyped-def]
    coros = [safe_async_runner(timeout=0.2)(build_coro(ret_val=-1, delay=0.3))()] + [
        safe_async_runner(timeout=0.2)(build_coro(ret_val, delay=0.1))() for ret_val in range(10)
    ]

    # expect raise timeout error, because the first coro is erroring out
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.gather(*coros)
    # when silent the runs, we should get results for all other coroutines
    coros = [safe_async_runner(timeout=0.2, silent=True)(build_coro(ret_val=-1, delay=0.3))()] + [
        safe_async_runner(timeout=0.2, silent=True)(build_coro(ret_val, delay=0.1))() for ret_val in range(10)
    ]
    results = await asyncio.gather(*coros)
    assert results == [None] + list(range(10))


@pytest.mark.asyncio
async def test_secure_gather_runner_retry():  # type: ignore[no-untyped-def]
    start = time.time()
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.gather(
            *[
                safe_async_runner(timeout=0.1, attempt=3, retry_delay=0.1)(  # type: ignore[arg-type]  # noqa: E501
                    build_coro(ret_val, delay=0.3)
                )()
                for ret_val in range(10)
            ]
        )
    duration = time.time() - start
    assert duration == pytest.approx(0.1 * 5, rel=0.05)


@pytest.mark.parametrize(
    "header_string, expected",
    [
        ('application/json; charset="utf8"', "application/json"),
        ("application/ld+json", "application/ld+json"),
        ("application/x-www-form-urlencoded; boundary=something", "application/x-www-form-urlencoded"),
    ],
)
def test_parse_content_type(header_string: str, expected: str):
    assert parse_content_type(header_string) == expected
