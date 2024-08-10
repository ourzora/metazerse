from typing import Optional, Tuple, Union

import httpx
import requests

from offchain.logger.logging import logger
from offchain.metadata.adapters import Adapter, AdapterConfig, DEFAULT_ADAPTER_CONFIGS
from offchain.metadata.fetchers.base_fetcher import BaseFetcher
from offchain.metadata.registries.fetcher_registry import FetcherRegistry
from offchain.utils.utils import parse_content_type


@FetcherRegistry.register
class MetadataFetcher(BaseFetcher):
    """Fetcher class that makes network requests for metadata-related information.

    Attributes:
        timeout (int): request timeout in seconds.
        max_retries (int): maximum number of request retries.
        sess (requests.Session): a requests Session object.
    """

    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 0,
        async_adapter_configs: Optional[list[AdapterConfig]] = DEFAULT_ADAPTER_CONFIGS,
    ) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self.sess = requests.Session()
        self.async_sess = httpx.AsyncClient()
        self.async_adapter_configs = async_adapter_configs

    def register_adapter(self, adapter: Adapter, url_prefix: str):  # type: ignore[no-untyped-def]  # noqa: E501
        """Register an adapter to a url prefix. Note this only affects synchronous http
        requests (via the requests library).

        Args:
            adapter (Adapter): an Adapter instance to register.
            url_prefix (str): the url prefix to which the adapter should be registered.
        """
        self.sess.mount(url_prefix, adapter)

    def set_max_retries(self, max_retries: int):  # type: ignore[no-untyped-def]
        """Setter function for max retries

        Args:
            max_retries (int): new maximum number of request retries.
        """
        self.max_retries = max_retries  # pragma: no cover

    def set_timeout(self, timeout: int):  # type: ignore[no-untyped-def]
        """Setter function for timeout

        Args:
            timeout (int): new request timeout in seconds.
        """
        self.timeout = timeout  # pragma: no cover

    def _get_async_adapter_for_uri(self, uri: str) -> Optional[Adapter]:
        if self.async_adapter_configs is None:
            logger.error("Async adapter config doesn't exist. This shouldn't happen!")
            return None

        for async_adapter_config in self.async_adapter_configs:
            if any(uri.startswith(prefix) for prefix in async_adapter_config.mount_prefixes):
                logger.debug(
                    f"Selected {async_adapter_config.adapter_cls.__name__} for making async http requests for uri={uri}"
                    # noqa: E501
                )
                return async_adapter_config.adapter_cls(
                    host_prefixes=async_adapter_config.host_prefixes,
                    **async_adapter_config.kwargs,
                )
        logger.warning(f"Unable to selected an adapter for async http requests for uri={uri}")
        return None

    def _head(self, uri: str):  # type: ignore[no-untyped-def]
        return self.sess.head(uri, timeout=self.timeout, allow_redirects=True)

    def _get(self, uri: str):  # type: ignore[no-untyped-def]
        return self.sess.get(uri, timeout=self.timeout, allow_redirects=True)

    async def _gen(self, uri: str, method: Optional[str] = "GET") -> httpx.Response:
        async_adapter = self._get_async_adapter_for_uri(uri)
        if async_adapter is not None:
            if method == "HEAD":
                return await async_adapter.gen_head(url=uri, timeout=self.timeout, sess=self.async_sess)
            else:
                return await async_adapter.gen_send(url=uri, timeout=self.timeout, sess=self.async_sess)
        return await self.async_sess.get(uri, timeout=self.timeout, follow_redirects=True)

    async def _gen_head(self, uri: str) -> httpx.Response:
        return await self._gen(uri=uri, method="HEAD")

    def fetch_mime_type_and_size(self, uri: str) -> Tuple[str, int]:
        """Fetch the mime type and size of the content at a given uri.

        Args:
            uri (str): uri from which to fetch content mime type and size.

        Returns:
            tuple[str, int]: mime type and size
        """
        try:
            res = self._head(uri)
            # For any error status, try a get
            if 300 <= res.status_code < 600:
                res = self._get(uri)
            res.raise_for_status()
            headers = res.headers
            size = headers.get("content-length", 0)
            content_type = headers.get("content-type") or headers.get("Content-Type")
            if content_type is not None:
                content_type = parse_content_type(content_type)

            return content_type, size
        except Exception as e:
            logger.error(f"Failed to fetch content-type and size from uri {uri}. Error: {e}")
            raise

    async def gen_fetch_mime_type_and_size(self, uri: str) -> Tuple[str, int]:
        """Fetch the mime type and size of the content at a given uri.

        Args:
            uri (str): uri from which to fetch content mime type and size.

        Returns:
            tuple[str, int]: mime type and size
        """
        try:
            res = await self._gen_head(uri)
            # For any error status, try a get
            if 300 <= res.status_code < 600:
                res = await self._gen(uri)
            res.raise_for_status()
            headers = res.headers
            size = headers.get("content-length", 0)
            content_type = headers.get("content-type") or headers.get("Content-Type")
            if content_type is not None:
                content_type = parse_content_type(content_type)

            return content_type, size
        except Exception as e:
            logger.error(f"Failed to fetch content-type and size from uri {uri}. Error: {e}")
            raise

    def fetch_content(self, uri: str) -> Union[dict, str]:  # type: ignore[type-arg]
        """Fetch the content at a given uri

        Args:
            uri (str): uri from which to fetch content.

        Returns:
            Union[dict, str]: content fetched from uri
        """
        try:
            res = self._get(uri)
            res.raise_for_status()
            if res.text.startswith("{"):
                return res.json()  # type: ignore[no-any-return]
            else:
                return res.text  # type: ignore[no-any-return]

        except Exception as e:
            raise Exception(f"Don't know how to fetch metadata for {uri=}. {str(e)}")

    async def gen_fetch_content(self, uri: str) -> Union[dict, str]:  # type: ignore[type-arg]  # noqa: E501
        """Async fetch the content at a given uri

        Args:
            uri (str): uri from which to fetch content.

        Returns:
            Union[dict, str]: content fetched from uri
        """
        try:
            res = await self._gen(uri)
            res.raise_for_status()
            if res.text.startswith("{"):
                return res.json()  # type: ignore[no-any-return]
            else:
                return res.text

        except Exception as e:
            raise Exception(f"Don't know how to fetch metadata for {uri=}. {str(e)}")
