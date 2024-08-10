# Core Concepts

This section will walk through the different components of `offchain` as well as how it works.
Please make sure to read this section first before diving into the rest of the documentation.

## Key Components

- [Pipeline](./pipeline/pipeline.md): Orchestrates the metadata fetching and normalizing process for multiple tokens.
- [Adapter](./pipeline/adapters.md): Parses the metadata url into an acceptable request format for the fetcher i.e. converting an IPFS Hash to a valid URL.
- [Fetcher](./pipeline/fetchers.md): Makes network requests to a given uri to fetch data.
- [Parser](./pipeline/parsers.md): Parses raw data into a standardized metadata format
- ContractCaller: Makes RPC calls to NFT contracts to retrieve the uri if not provided.

## Parser Types

- `CollectionParsers`: Used for specific NFT contract addresses that have unique metadata e.g. Autoglphys, Nouns, and ENS.
- `SchemaParsers`: Used for general purpose formatting across many NFT collections e.g. Opensea Metadata Standard.

## How Offchain Works

An overview of how offchain retrieves NFT metadata.

1. The `Pipeline` is initialized with a `ContractCaller`, a `Fetcher`, a list of `Adapters`, and a list of `Parsers`.
2. An array of `Tokens` is passed into the pipeline to fetch.
3. If no `uri` is provided for the tokens, the `ContractCaller` will fetch it by calling `tokenURI(uint256)` on the contract.
4. The `Adapters` to attempt to format the uri into a valid url.
5. The `Fetcher` then makes a request to the url and attempts to get JSON metadata for the token.
6. The `Parsers` attempt to parse the token metadata into an acceptable format.
7. Each parser runs in the order they were passed in. By default, the ordering is `CollectionParsers`, `SchemaParsers`, and then `CatchallParsers`.
8. The pipeline returns the result from the first parser that is successful, unless a `metadata_selector_fn` is specified.
9. However, the pipeline returns a [`MetadataProcessingError`](./models/metadata_processing_error.md) if no parser is successful for that specific token.

## Token Interface

This interface is how an NFT is passed into the pipeline for fetching.

- `collection_address`: The token's contract address.
- `token_id`: The unique identifier for a token within a collection.
- `chain_identifier`: The network and chain for the token. Defaults to "ETHEREUM-MAINNET" if nothing is passed in.
- `uri`: The url where the metadata lives. Defaults to fetching from the contract directly if nothing is passed in.

```python
# Gets metadata for Azuki #40

from offchain.metadata.pipelines.metadata_pipeline import MetadataPipeline
from offchain.metadata.models.token import Token

pipeline = MetadataPipeline()
token = Token(
    collection_address="0xED5AF388653567Af2F388E6224dC7C4b3241C544",
    token_id=40,
    chain_identifier="ETHEREUM-MAINNET",
    uri="https://ikzttp.mypinata.cloud/ipfs/QmQFkLSQysj94s5GvTHPyzTxrawwtjgiiYS2TBLgrvw8CW/40"
)

metadata = pipeline.run([token])[0]
```

## RPC Provider

By default, the pipeline uses `https://cloudflare-eth.com` as the provider for the `ContractCaller`.
This is a free Ethereum RPC provider, which means that it is very easy to exceed the rate-limit.
The code below illustrates how to use a custom RPC provider to prevent getting rate-limited if token uris need to be retrieved from the contract:

```python
from offchain import MetadataPipeline
from offchain.web3.contract_caller import ContractCaller
from offchain.web3.jsonrpc import EthereumJSONRPC

rpc = EthereumJSONRPC(provider_url=MY_PROVIDER_URL)
contract_caller = ContractCaller(rpc=rpc)
pipeline = MetadataPipeline(contract_caller=contract_caller)
```

<br/>

Next, check out the [`Usage`](./usage/overview.md) section to see how to use `offchain`.

<br/>
