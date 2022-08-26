from dataclasses import dataclass
from typing import Callable, Optional, Union

from offchain.concurrency import batched_parmap
from offchain.metadata.adapters import (
    ARWeaveAdapter,
    DataURIAdapter,
    HTTPAdapter,
    IPFSAdapter,
)
from offchain.metadata.adapters.base_adapter import Adapter
from offchain.metadata.fetchers.base_fetcher import BaseFetcher
from offchain.metadata.fetchers.metadata_fetcher import MetadataFetcher
from offchain.metadata.models.metadata import Metadata
from offchain.metadata.models.metadata_processing_error import MetadataProcessingError
from offchain.metadata.models.token import Token
from offchain.metadata.parsers import OpenseaParser
from offchain.metadata.parsers.base_parser import BaseParser
from offchain.metadata.parsers.schema.unknown import UnknownParser
from offchain.metadata.pipelines.base_pipeline import BasePipeline


@dataclass
class AdapterConfig:
    adapter: Adapter
    mount_prefixes: list[str]


DEFAULT_ADAPTER_CONFIGS: list[AdapterConfig] = [
    AdapterConfig(
        adapter=ARWeaveAdapter(pool_connections=100, pool_maxsize=1000, max_retries=0),
        mount_prefixes=["ar://"],
    ),
    AdapterConfig(adapter=DataURIAdapter(), mount_prefixes=["data:"]),
    AdapterConfig(
        adapter=HTTPAdapter(pool_connections=100, pool_maxsize=1000, max_retries=0),
        mount_prefixes=["https://", "http://"],
    ),
    AdapterConfig(
        adapter=IPFSAdapter(pool_connections=100, pool_maxsize=1000, max_retries=0),
        mount_prefixes=[
            "ipfs://",
            "https://gateway.pinata.cloud/",
            "https://ipfs.io/",
        ],
    ),
]

DEFAULT_PARSER_CLASSES = [OpenseaParser, UnknownParser]


class MetadataPipeline(BasePipeline):
    """Base protocol for Pipeline classes

    By default, the parsers are run in order and we will early return when of them returns a valid metadata object.

    Attributes:
        fetcher (BaseFetcher, optional): a fetcher instance responsible for fetching content,
            mime type, and size by making requests.
        parsers (list[BaseParser], optional): a list of parser instances to use to parse token metadata.
        adapter_configs: (list[AdapterConfig], optional): a list of adapter configs used to register adapters
            to specified url prefixes.
    """

    def __init__(
        self,
        fetcher: Optional[BaseFetcher] = None,
        parsers: Optional[list[BaseParser]] = None,
        adapter_configs: Optional[list[AdapterConfig]] = None,
    ) -> None:
        self.fetcher = fetcher or MetadataFetcher()
        if adapter_configs is None:
            adapter_configs = DEFAULT_ADAPTER_CONFIGS
        for adapter_config in adapter_configs:
            self.mount_adapter(
                adapter=adapter_config.adapter,
                url_prefixes=adapter_config.mount_prefixes,
            )
        if parsers is None:
            parsers = [parser_cls(fetcher=self.fetcher) for parser_cls in DEFAULT_PARSER_CLASSES]
        self.parsers = parsers

    def mount_adapter(
        self,
        adapter: Adapter,
        url_prefixes: list[str],
    ):
        """Given an adapter and list of url prefixes, register the adapter to each of the prefixes.

        Example Usage: mount_adapter(IPFSAdapter, ["ipfs://", "https://gateway.pinata.cloud/"])

        Args:
            adapter (Adapter): Adapter instance
            url_prefixes (list[str]): list of url prefixes to which to mount the adapter.
        """
        for prefix in url_prefixes:
            self.fetcher.register_adapter(adapter, prefix)

    def fetch_token_metadata(
        self,
        token: Token,
        metadata_selector_fn: Optional[Callable] = None,
    ) -> Union[Metadata, MetadataProcessingError]:
        """Fetch metadata for a single token

        Args:
            token (Token): token for which to fetch metadata.
            metadata_selector_fn (Optional[Callable], optional):
                optionally specify a function to select a metadata
                object from a list of metadata. Defaults to None.

        Returns:
            Union[Metadata, MetadataProcessingError]: returns either a Metadata
                or a MetadataProcessingError if unable to parse.
        """
        raw_data = self.fetcher.fetch_content(token.uri)
        possible_metadatas = []
        for parser in self.parsers:
            if parser.should_parse_token(token=token, raw_data=raw_data):
                try:
                    metadata_or_error = parser.parse_metadata(token=token, raw_data=raw_data)
                    if metadata_selector_fn is None:
                        return metadata_or_error
                except Exception as e:
                    metadata_or_error = MetadataProcessingError.from_token_and_error(token=token, e=e)
                possible_metadatas.append(metadata_or_error)
        if len(possible_metadatas) == 0:
            possible_metadatas.append(
                MetadataProcessingError.from_token_and_error(token=token, e=Exception("No parsers found."))
            )

        if metadata_selector_fn:
            return metadata_selector_fn(possible_metadatas)
        return possible_metadatas[0]

    def run(
        self,
        tokens: list[Token],
        parallelize: bool = True,
        select_metadata_fn: Optional[Callable] = None,
        *args,
        **kwargs,
    ) -> list[Union[Metadata, MetadataProcessingError]]:
        """Run metadata pipeline on a list of tokens.

        Args:
            tokens (list[Token]): tokens for which to process metadata.
            parallelize (bool, optional): whether or not metadata should be processed in parallel.
                Defaults to True. Turn off parallelization to reduce risk of getting rate-limited.
            select_metadata_fn (Optional[Callable], optional): optionally specify a function to
                select a metadata object from a list of metadata. Defaults to None. Defaults to None.

        Returns:
            list[Union[Metadata, MetadataProcessingError]]: returns a list of Metadatas
                or MetadataProcessingErrors that map 1:1 to the tokens passed in.
        """
        if len(tokens) == 0:
            return []

        if parallelize:
            metadatas_or_errors = batched_parmap(lambda t: self.fetch_token_metadata(t, select_metadata_fn), tokens, 15)
        else:
            metadatas_or_errors = list(map(lambda t: self.fetch_token_metadata(t, select_metadata_fn), tokens))

        return metadatas_or_errors
