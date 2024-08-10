# Contributing a Collection Parser

A guide on how to contribute a collection parser.

---

## Step 1: Determine the Type of Parser

Before implementing your parser, familiarize yourself with the [BaseParser](../pipeline/parsers.md#baseparser), [CollectionParser](../pipeline/parsers.md#collectionparser), and [SchemaParser](../pipeline/parsers.md#schemaparser) base classes.

A parser will be one of the following:

- `CollectionParser`: Runs based on a token's contract address.
- `SchemaParser`: Runs based on the shape of the token's metadata.

We're building a `CollectionParser` for ENS because it is the only NFT collection that uses this metadata schema.
Collection parsers are great for one-off collections with unique metadata.

```python
class ENSParser(CollectionParser):
    pass
```

---

## Step 2: Define the Selection Criteria

The next step is to define your parser's selection criteria.
This tells the pipeline which tokens to run your parser on.

The selection criteria for a collection parser is defined by a `_COLLECTION_ADDRESSES` class variable, which tells the parser which collection address(es) to run on. The ENS collection parser will only run on tokens with the ENS contract address `0x57f1887a8BF19b14fC0dF6Fd9B2acc9Af147eA85`.

```python
class ENSParser(CollectionParser):
    _COLLECTION_ADDRESSES: list[str] = ["0x57f1887a8BF19b14fC0dF6Fd9B2acc9Af147eA85"]
```

---

## Step 3: Write the Parsing Implementation

### Step 3a: Construct the Token URI

The token uri is needed to tell the parser where to fetch the metadata from.
If the token uri is not passed in as part of the input, the pipeline will attempt to fetch it from the `tokenURI(uint256)` function on the contract.

Note, it is not uncommon for token uris to be base64 encoded data is stored entirely on chain e.g. Nouns, Zorbs.

ENS hosts their own metadata service and token uris are constructed in the following format:

`https://metadata.ens.domains/<chain_name>/<collection_address>/<token_id>/`

```python
class ENSParser(CollectionParser):
    _COLLECTION_ADDRESSES: list[str] = ["0x57f1887a8BF19b14fC0dF6Fd9B2acc9Af147eA85"]

    @staticmethod
    def make_ens_chain_name(chain_identifier: str):
        try:
            return chain_identifier.split("-")[1].lower()
        except Exception:
            logger.error(f"Received unexpected chain identifier: {chain_identifier}")
            return "mainnet"

    def parse_metadata(self, token: Token, raw_data: dict, *args, **kwargs) -> Optional[Metadata]:
        ens_chain_name = self.make_ens_chain_name(token.chain_identifier)

        token.uri = (
            f"https://metadata.ens.domains/{ens_chain_name}/{token.collection_address.lower()}/{token.token_id}/"
        )
```

Let's use this ENS NFT as an example:

```python
Token(
    chain_identifier="ETHEREUM-MAINNET",
    collection_address="0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85",
    token_id=10110056301157368922112380646085332716736091604887080310048917803187113883396,
)
```

If we pass it into the parser, we'll get the following uri:
`https://metadata.ens.domains/mainnet/0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85/10110056301157368922112380646085332716736091604887080310048917803187113883396`

### Step 3b: Fetch Metadata From the Token URI

Now we can use the `Fetcher` to get the raw JSON data from the token uri.
By default, the parser is initialized with a `Fetcher` instance with an HTTP adapter.

```python
    raw_data = self.fetcher.fetch_content(token.uri)
```

This should return the following data from the ENS metadata service:

```json
{
  "is_normalized": true,
  "name": "steev.eth",
  "description": "steev.eth, an ENS name.",
  "attributes": [
    {
      "trait_type": "Created Date",
      "display_type": "date",
      "value": 1633123738000
    },
    { "trait_type": "Length", "display_type": "number", "value": 5 },
    { "trait_type": "Segment Length", "display_type": "number", "value": 5 },
    {
      "trait_type": "Character Set",
      "display_type": "string",
      "value": "letter"
    },
    {
      "trait_type": "Registration Date",
      "display_type": "date",
      "value": 1633123738000
    },
    {
      "trait_type": "Expiration Date",
      "display_type": "date",
      "value": 1822465450000
    }
  ],
  "name_length": 5,
  "segment_length": 5,
  "url": "https://app.ens.domains/name/steev.eth",
  "version": 0,
  "background_image": "https://metadata.ens.domains/mainnet/avatar/steev.eth",
  "image": "https://metadata.ens.domains/mainnet/0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85/0x165a16ce2915e51295772b6a67bfc8ceee2c1c7caa85591fba107af4ee24f704/image",
  "image_url": "https://metadata.ens.domains/mainnet/0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85/0x165a16ce2915e51295772b6a67bfc8ceee2c1c7caa85591fba107af4ee24f704/image"
}
```

### Step 3c: Standardize the New Metadata Format

The next step is to convert the metadata into the [standardized metadata format](../models/metadata.md).

Each field in the new metadata format should either map a field in the standardized metadata format or be added as an `MetadataField` under the `additional_fields` property.

In the case of ENS, the metadata format has the following fields:

```json
{
  "name": "ENS name",
  "description": "Short ENS name description",
  "attributes": "Custom traits about ENS",
  "name_length": "Character length of ens name",
  "url": "ENS App URL of the name",
  "version": "ENS NFT version",
  "background_image": "Origin URL of avatar image",
  "image_url": "URL of ENS NFT image"
}
```

Each of these fields can be mapped into the standard metadata format:

| Standard Metadata Field | New Metadata Field        |
| ----------------------- | ------------------------- |
| token                   |                           |
| raw_data                |                           |
| standard                |                           |
| attributes              | attributes                |
| name                    | name                      |
| description             | description               |
| mime_type               |                           |
| image                   | image_url                 |
| content                 | background_image          |
| additional_fields       | name_length, url, version |

---

And this is how it would look programmatically:

```python
class ENSParser(CollectionParser):
    _COLLECTION_ADDRESSES: list[str] = ["0x57f1887a8BF19b14fC0dF6Fd9B2acc9Af147eA85"]

    @staticmethod
    def make_ens_chain_name(chain_identifier: str):
        try:
            return chain_identifier.split("-")[1].lower()
        except Exception:
            logger.error(f"Received unexpected chain identifier: {chain_identifier}")
            return "mainnet"

    def get_additional_fields(self, raw_data: dict) -> list[MetadataField]:
        additional_fields = []
        if name_length := raw_data.get("name_length"):
            additional_fields.append(
                MetadataField(
                    field_name="name_length",
                    type=MetadataFieldType.TEXT,
                    description="Character length of ens name",
                    value=name_length,
                )
            )
        if version := raw_data.get("version"):
            additional_fields.append(
                MetadataField(
                    field_name="version",
                    type=MetadataFieldType.TEXT,
                    description="ENS NFT version",
                    value=version,
                )
            )
        if url := raw_data.get("url"):
            additional_fields.append(
                MetadataField(
                    field_name="url",
                    type=MetadataFieldType.TEXT,
                    description="ENS App URL of the name",
                    value=url,
                )
            )
        return additional_fields

    def parse_attributes(self, raw_data: dict) -> Optional[list[Attribute]]:
        attributes = raw_data.get("attributes")
        if not attributes or not isinstance(attributes, list):
            return

        return [
            Attribute(
                trait_type=attribute_dict.get("trait_type"),
                value=attribute_dict.get("value"),
                display_type=attribute_dict.get("display_type"),
            )
            for attribute_dict in attributes
        ]

    def get_image(self, raw_data: dict) -> Optional[MediaDetails]:
        image_uri = raw_data.get("image_url") or raw_data.get("image")
        if image_uri:
            image = MediaDetails(uri=image_uri, size=None, sha256=None, mime_type=None)
            try:
                content_type, size = self.fetcher.fetch_mime_type_and_size(image_uri)
                image.mime_type = content_type
                image.size = size
                return image
            except Exception:
                pass

    def get_background_image(self, raw_data: dict) -> Optional[MediaDetails]:
        bg_image_uri = raw_data.get("background_image")
        if bg_image_uri:
            image = MediaDetails(uri=bg_image_uri, size=None, sha256=None, mime_type=None)
            try:
                content_type, size = self.fetcher.fetch_mime_type_and_size(bg_image_uri)
                image.mime_type = content_type
                image.size = size
                return image
            except Exception:
                pass

    def parse_metadata(self, token: Token, raw_data: dict, *args, **kwargs) -> Optional[Metadata]:
        ens_chain_name = self.make_ens_chain_name(token.chain_identifier)

        token.uri = (
            f"https://metadata.ens.domains/{ens_chain_name}/{token.collection_address.lower()}/{token.token_id}/"
        )
        raw_data = self.fetcher.fetch_content(token.uri)
        mime_type, _ = self.fetcher.fetch_mime_type_and_size(token.uri)

        return Metadata(
            token=token,
            raw_data=raw_data,
            attributes=self.parse_attributes(raw_data),
            name=raw_data.get("name"),
            description=raw_data.get("description"),
            mime_type=mime_type,
            image=self.get_image(raw_data=raw_data),
            content=self.get_background_image(raw_data=raw_data),
            additional_fields=self.get_additional_fields(raw_data=raw_data),
        )

```

---

## Step 4: Registering a Parser

After writing your custom parser, you'll want to register it to the `ParserRegistry`.

The `ParserRegistry` tracks all parsers and is used by the metadata pipeline to know which parsers to run by default.

```python
@ParserRegistry.register
class ENSParser(CollectionParser):
    ...
```

Note, in order to have the parser be registered, you'll also need to import it in `offchain/metadata/parsers/__init__.py`.

If you're developing locally, you still need to import the `ParserRegistry` to register your parser. The parser must be registered in order for it to be run by default in the `MetadataPipeline`. In the example below, we register the `ENSParser` class locally and run `get_token_metadata()`, which leverages the `MetadataPipeline`.

```python
from offchain import get_token_metadata
from offchain.metadata import CollectionParser
from offchain.metadata.registries.parser_registry import ParserRegistry

@ParserRegistry.register
class ENSParser(CollectionParser):
    ...

get_token_metadata(
    collection_address="0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85",
    token_id=10110056301157368922112380646085332716736091604887080310048917803187113883396,
    chain_identifier="ETHEREUM-MAINNET"
)
```

---

## Step 5: Testing the Parser

### Step 5a: Write Unit Tests

You'll want to write tests to verify that your parser works as expected. At minimum, the `should_parse_token()` and `parse_metadata()` functions should be tested because the pipeline will call those directly.

It's important to verify that the `should_parse_token()` function returns `True` if and only if a token is meant to be parsed by that parser.

Given a token, `parse_metadata()` should normalize the raw data into the standardized metadata format. Since making network requests can be flaky, it's preferable to mock the data that would be returned by the server that hosts the metadata information.

```python
def test_ens_parser_should_parse_token(self):
    fetcher = MetadataFetcher()
    contract_caller = ContractCaller()
    parser = ENSParser(fetcher=fetcher, contract_caller=contract_caller)
    assert parser.should_parse_token(token=token) == True

def test_ens_parser_parses_metadata(self):
    fetcher = MetadataFetcher()
    contract_caller = ContractCaller()
    fetcher.fetch_mime_type_and_size = MagicMock(return_value=("application/json", 41145))
    fetcher.fetch_content = MagicMock(return_value=mocked_raw_data)
    parser = ENSParser(fetcher=fetcher, contract_caller=contract_caller)
    assert parser.parse_metadata(token=token, raw_data=None) == expected_metadata
```

In addition to testing your parser, you'll need to verify that the parser has been registered and added to the pipeline correctly. The tests in `tests/metadata/registries/test_parser_registry.py` should break if the not modified to include your new parser class.

---

### Step 5b: Testing Manually

It's always good practice to test manually as well. We can set up our pipeline using the example NFT from earlier:

```python
from offchain.metadata.pipelines.metadata_pipeline import MetadataPipeline
from offchain.metadata.models.token import Token

pipeline = MetadataPipeline()
token = Token(
    chain_identifier="ETHEREUM-MAINNET",
    collection_address="0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85",
    token_id=10110056301157368922112380646085332716736091604887080310048917803187113883396,
)
metadata = pipeline.run([token])[0]
```

This should give us the following standardized metadata:

```python
Metadata(
    token=Token(
        collection_address='0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85'
        token_id=10110056301157368922112380646085332716736091604887080310048917803187113883396,
        chain_identifier='ETHEREUM-MAINNET',
        uri='https://metadata.ens.domains/mainnet/0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85/10110056301157368922112380646085332716736091604887080310048917803187113883396/'
    ),
    raw_data={
        'is_normalized': True,
        'name': 'steev.eth',
        'description': 'steev.eth, an ENS name.',
        'attributes': [
            {
                'trait_type': 'Created Date',
                'display_type': 'date',
                'value': 1633123738000
            },
            {
                'trait_type': 'Length',
                'display_type': 'number',
                'value': 5
            },
            {
                'trait_type': 'Segment Length',
                'display_type': 'number',
                'value': 5
            },
            {
                'trait_type': 'Character Set',
                'display_type': 'string',
                'value': 'letter'
            },
            {
                'trait_type': 'Registration Date',
                'display_type': 'date',
                'value': 1633123738000
            },
            {
                'trait_type': 'Expiration Date',
                'display_type': 'date',
                'value': 1822465450000
                }
        ],
        'name_length': 5,
        'segment_length': 5,
        'url': 'https://app.ens.domains/name/steev.eth',
        'version': 0,
        'background_image': 'https://metadata.ens.domains/mainnet/avatar/steev.eth',
        'image': 'https://metadata.ens.domains/mainnet/0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85/0x165a16ce2915e51295772b6a67bfc8ceee2c1c7caa85591fba107af4ee24f704/image',
        'image_url': 'https://metadata.ens.domains/mainnet/0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85/0x165a16ce2915e51295772b6a67bfc8ceee2c1c7caa85591fba107af4ee24f704/image'
    },
    attributes=[
        Attribute(trait_type='Created Date', value='1633123738000', display_type='date'),
        Attribute(trait_type='Length', value='5', display_type='number'),
        Attribute(trait_type='Segment Length', value='5', display_type='number'),
        Attribute(trait_type='Character Set', value='letter', display_type='string'),
        Attribute(trait_type='Registration Date', value='1633123738000', display_type='date'),
        Attribute(trait_type='Expiration Date', value='1822465450000', display_type='date')
    ],
    standard=COLLECTION_STANDARD,
    name='steev.eth',
    description='steev.eth, an ENS name.',
    mime_type='application/json',
    image=MediaDetails(
        size=0,
        sha256=None,
        uri='https://metadata.ens.domains/mainnet/0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85/0x165a16ce2915e51295772b6a67bfc8ceee2c1c7caa85591fba107af4ee24f704/image',
        mime_type='image/svg+xml'
    ),
    content=MediaDetails(
        size=0,
        sha256=None,
        uri='https://metadata.ens.domains/mainnet/avatar/steev.eth',
        mime_type=None
    ),
    additional_fields=[
        MetadataField(
            field_name='name_length',
            type=TEXT,
            description='Character length of ens name',
            value=5
        ),
        MetadataField(
            field_name='url',
            type=TEXT,
            description='ENS App URL of the name',
            value='https://app.ens.domains/name/steev.eth'
        )
    ]
)

```

## ENS collection parser source code

::: offchain.metadata.parsers.collection.ens.ENSParser
