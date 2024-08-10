import asyncio
import traceback
from typing import Optional, TypeVar

from offchain.logger.logging import logger

T = TypeVar("T")


def nullthrows(value: Optional[T], msg="Value is None") -> T:  # type: ignore[no-untyped-def]  # noqa: E501
    if value is None:
        stack = "\n".join(traceback.format_stack())
        msg = f"{msg=} stacktrace={stack}"
        logger.error(msg)
        raise ValueError(msg)
    return value


def safe_async_runner(  # type: ignore[no-untyped-def]
    attempt: int = 1,
    retry_delay: int = 0,
    timeout: Optional[float] = None,
    silent: bool = False,
):
    def wrapper(fn):  # type: ignore[no-untyped-def]
        async def wrapped(*args, **kwargs):  # type: ignore[no-untyped-def]
            for i in range(attempt):
                try:
                    return await asyncio.wait_for(fn(*args, **kwargs), timeout=timeout)
                except Exception:
                    msg = (
                        f"Caught exception while executing async function {fn}: {traceback.format_exc()}"  # noqa: E501
                    )
                    if i + 1 == attempt:
                        logger.error(msg)
                        if not silent:
                            raise
                    logger.warning(msg)
                    await asyncio.sleep(retry_delay)
            return None

        return wrapped

    return wrapper


def parse_content_type(header_string: str) -> str:
    from email.message import EmailMessage

    msg = EmailMessage()
    msg["content-type"] = header_string
    return msg.get_content_type()
