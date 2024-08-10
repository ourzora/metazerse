# Contributing a Schema Parser

A guide on how to contribute a schema parser.

We'll learn how to build a parser for NFTs that follow the [OpenSea Metadata Standard](https://docs.opensea.io/docs/metadata-standards#metadata-structure) and go over important considerations.

---

## Step 1: Determine the Type of Parser

Before implementing your parser, familiarize yourself with the [BaseParser](../pipeline/parsers.md#baseparser), [CollectionParser](../pipeline/parsers.md#collectionparser), and [SchemaParser](../pipeline/parsers.md#schemaparser) base classes.

A parser will be one of the following:

- `CollectionParser`: Runs based on a token's contract address.
- `SchemaParser`: Runs based on the shape of the token's metadata.

Since, we're building a parser for NFTs that follow the [OpenSea Metadata Standard](https://docs.opensea.io/docs/metadata-standards#metadata-structure), we'll use a `SchemaParser`.
Schema parsers are used for metadata standards that will be used across many different NFT collections.

```python
class OpenseaParser(SchemaParser):
```

---

## Step 2: Define the Selection Criteria

The next step is to define your parser's selection criteria. This tells the pipeline which tokens to run your parser on.

For a schema parser you'll need to override the `should_parse_token()` method of `BaseParser` to implement custom selection logic based on the shape of the metadata.

For instance, if the new metadata schema contains a unique field, checking for the existence of that field would qualify as selection criteria.
In this case both `background_color` and `youtube_url` are criteria for checking if an NFT follows the [OpenSea Metadata Standard](https://docs.opensea.io/docs/metadata-standards#metadata-structure).

```python
def should_parse_token(self, token: Token, raw_data: Optional[dict], *args, **kwargs) -> bool:
    """Return whether or not a collection parser should parse a given token.
    Args:
        token (Token): the token whose metadata needs to be parsed.
        raw_data (dict): raw data returned from token uri.
    Returns:
        bool: whether or not the collection parser handles this token.
    """
    return (
        raw_data is not None
        and isinstance(raw_data, dict)
        and (raw_data.get("background_color") is not None or raw_data.get("youtube_url") is not None)
    )
```

---

## Step 3: Write the Parsing Implementation

If the token uri is not passed in as part of the input, the pipeline will attempt to fetch it from the `tokenURI(uint256)` function on the contract. Otherwise, it is expected that the parser will construct the token uri.

Let's use the Song a Day collection as an example:

```python
Token(
    chain_identifier="ETHEREUM-MAINNET",
    collection_address="0x19b703f65aa7e1e775bd06c2aa0d0d08c80f1c45",
    token_id=1351,
)
```

If we pass it into the parser, we'll get the following uri: `ipfs://Qmb9X7yBk5iKzgnS5pfAfReFT8FVaLcf7cJGxxUFWzRMyk/1351`, which returns metadata for token #1351.

Once you have the token uri, we can use the `Fetcher` to fetch the raw JSON data from the token uri.
By default, the parser is initialized with a `Fetcher` instance with an IPFS adapter.

```python
    raw_data = self.fetcher.fetch_content(token.uri)
```

This should return the following data from the IPFS Gateway:

```json
{
  "name": "Obligatory Song About the iPhone 5",
  "description": "A new song, everyday, forever. Song A Day is an ever-growing collection of unique songs created by Jonathan Mann, starting January 1st, 2009. Each NFT is a 1:1 representation of that days song, and grants access to SongADAO, the organization that controls all the rights and revenue to the songs. Own a piece of the collection to help govern the future of music. http://songaday.world",
  "token_id": 1351,
  "image": "ipfs://QmX2ZdS13khEYqpC8Jz4nm7Ub3He3g5Ws22z3QhunC2k58/1351",
  "animation_url": "ipfs://QmVHjFbGEqXfYuoPpJR4vmRacGM29KR5UenqbidJex8muB/1351",
  "external_url": "https://songaday.world/song/1351",
  "youtube_url": "https://www.youtube.com/watch?v=xBOaUo1GT0g",
  "attributes": [
    { "trait_type": "Date", "value": "2012-09-12" },
    { "trait_type": "Location", "value": "Brooklyn Studio" },
    { "trait_type": "Topic", "value": "Apple" },
    { "trait_type": "Instrument", "value": "Electric Guitar" },
    { "trait_type": "Mood", "value": "Bored" },
    { "trait_type": "Beard", "value": "Shadow" },
    { "trait_type": "Genre", "value": "Rock" },
    { "trait_type": "Style", "value": "Fun" },
    { "trait_type": "Length", "value": "0:47" },
    { "trait_type": "Key", "value": "E" },
    { "trait_type": "Tempo", "value": "90" },
    { "trait_type": "Song A Day", "value": "1351" },
    { "trait_type": "Year", "value": "2012" },
    { "trait_type": "Instrument", "value": "Bass" },
    { "trait_type": "Instrument", "value": "Drums" },
    { "trait_type": "Style", "value": "Catchy" },
    { "trait_type": "Proper Noun", "value": "iPhone" }
  ]
}
```

The next step is to convert the metadata into the [standardized metadata format](../models/metadata.md).

Each field in the new metadata format should either map a field in the standardized metadata format or be added as an `MetadataField` under the `additional_fields` property.

In the case of Song a Day, the metadata format has the following fields:

```json
{
  "name": "NFT name",
  "description": "More info about the NFT",
  "attributes": "Custom traits",
  "image": "Image media asset",
  "animation_url": "Media asset for videos",
  "external_url": "External linking",
  "youtube_url": "Video on hosted on Youtube"
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
| image                   | image                     |
| content                 | animation_url             |
| additional_fields       | external_url, youtube_url |

---

Code used for parsing collections that use the [OpenSea Metadata Standard](https://docs.opensea.io/docs/metadata-standards#metadata-structure):

```python
def parse_metadata(self, token: Token, raw_data: dict, *args, **kwargs) -> Optional[Metadata]:
    """Given a token and raw data returned from the token uri, return a normalized Metadata object.
    Args:
        token (Token): token to process metadata for.
        raw_data (dict): raw data returned from token uri.
    Returns:
        Optional[Metadata]: normalized metadata object, if successfully parsed.
    """
    mime, _ = self.fetcher.fetch_mime_type_and_size(token.uri)

    attributes = [self.parse_attribute(attribute) for attribute in raw_data.get("attributes", [])]
    image = None
    image_uri = raw_data.get("image") or raw_data.get("image_data")
    if image_uri:
        image_mime, image_size = self.fetcher.fetch_mime_type_and_size(image_uri)
        image = MediaDetails(size=image_size, uri=image_uri, mime_type=image_mime)

    content = None
    content_uri = raw_data.get("animation_url")
    if content_uri:
        content_mime, content_size = self.fetcher.fetch_mime_type_and_size(content_uri)
        content = MediaDetails(uri=content_uri, size=content_size, mime_type=content_mime)

    if image and image.mime_type:
        mime = image.mime_type

    if content and content.mime_type:
        mime = content.mime_type

    return Metadata(
        token=token,
        raw_data=raw_data,
        attributes=attributes,
        name=raw_data.get("name"),
        description=raw_data.get("description"),
        mime_type=mime,
        image=image,
        content=content,
        additional_fields=self.parse_additional_fields(raw_data),
    )

# Helper Functions
def parse_attribute(self, attribute_dict: dict) -> Attribute:
    return Attribute(
        trait_type=attribute_dict.get("trait_type"),
        value=attribute_dict.get("value"),
        display_type=attribute_dict.get("display_type"),
    )

def parse_additional_fields(self, raw_data: dict) -> list[MetadataField]:
    additional_fields = []
    if (external_url := raw_data.get("external_url")) is not None:
        additional_fields.append(
            MetadataField(
                field_name="external_url",
                type=MetadataFieldType.TEXT,
                description="This is the URL that will appear below the asset's image on OpenSea "
                "and will allow users to leave OpenSea and view the item on your site.",
                value=external_url,
            )
        )
    if (background_color := raw_data.get("background_color")) is not None:
        additional_fields.append(
            MetadataField(
                field_name="background_color",
                type=MetadataFieldType.TEXT,
                description="Background color of the item on OpenSea. Must be a six-character "
                "hexadecimal without a pre-pended #.",
                value=background_color,
            )
        )
    if (animation_url := raw_data.get("animation_url")) is not None:
        additional_fields.append(
            MetadataField(
                field_name="animation_url",
                type=MetadataFieldType.TEXT,
                description="A URL to a multi-media attachment for the item.",
                value=animation_url,
            )
        )
    if (youtube_url := raw_data.get("youtube_url")) is not None:
        additional_fields.append(
            MetadataField(
                field_name="youtube_url",
                type=MetadataFieldType.TEXT,
                description="A URL to a YouTube video.",
                value=youtube_url,
            )
        )
    return additional_fields
```

---

## Step 4: Registering a Parser

After writing your custom metadata parser implementation, you'll want to register it to the `ParserRegistry`.

The `ParserRegistry` tracks all parsers and is used by the metadata pipeline to know which parsers to run by default.

```python
@ParserRegistry.register
class OpenseaParser(SchemaParser):
    ...
```

Note: in order to have the parser be registered, you'll also need to import it in `offchain/metadata/parsers/__init__.py`.

If you're developing locally, you still need to import the `ParserRegistry` to register your parser. The parser must be registered in order for it to be run by default in the `MetadataPipeline`.

---

## Step 5: Testing the Parser

Lastly, you'll want to write tests to verify that your parser works as expected. At minimum, the `should_parse_token()` and `parse_metadata()` functions should be tested because the pipeline will call those directly.

It's important to verify that the `should_parse_token()` function returns `True` if and only if a token is meant to be parsed by that parser.

Given a token, `parse_metadata()` should normalize the raw data into the standardized metadata format. Since making network requests can be flaky, it's preferable to mock the data that would be returned by the server that hosts the metadata information.

```python
def test_opensea_parser_should_parse_token(self, raw_crypto_coven_metadata):
    fetcher = MetadataFetcher()
    ipfs_adapter = IPFSAdapter()
    fetcher.register_adapter(ipfs_adapter, "ipfs://")
    parser = OpenseaParser(fetcher=fetcher)
    assert parser.should_parse_token(token=self.token, raw_data=raw_crypto_coven_metadata) == True

def test_opensea_parser_parses_metadata(self, raw_crypto_coven_metadata):
    fetcher = MetadataFetcher()
    ipfs_adapter = IPFSAdapter()
    fetcher.register_adapter(ipfs_adapter, "ipfs://")
    fetcher.fetch_mime_type_and_size = MagicMock(return_value=("application/json", "3095"))
    parser = OpenseaParser(fetcher=fetcher)
    metadata = parser.parse_metadata(token=self.token, raw_data=raw_crypto_coven_metadata)
    assert metadata == Metadata(
        token=self.token,
        raw_data=raw_crypto_coven_metadata,
        standard=None,
        attributes=[
            Attribute(trait_type="Background", value="Sepia", display_type=None),
            Attribute(trait_type="Skin Tone", value="Dawn", display_type=None),
            Attribute(trait_type="Body Shape", value="Lithe", display_type=None),
            Attribute(trait_type="Top", value="Sheer Top (Black)", display_type=None),
            Attribute(
                trait_type="Eyebrows",
                value="Medium Flat (Black)",
                display_type=None,
            ),
            Attribute(trait_type="Eye Style", value="Nyx", display_type=None),
            Attribute(trait_type="Eye Color", value="Cloud", display_type=None),
            Attribute(trait_type="Mouth", value="Nyx (Mocha)", display_type=None),
            Attribute(trait_type="Hair (Front)", value="Nyx", display_type=None),
            Attribute(trait_type="Hair (Back)", value="Nyx Long", display_type=None),
            Attribute(trait_type="Hair Color", value="Steel", display_type=None),
            Attribute(trait_type="Hat", value="Witch (Black)", display_type=None),
            Attribute(
                trait_type="Necklace",
                value="Moon Necklace (Silver)",
                display_type=None,
            ),
            Attribute(
                trait_type="Archetype of Power",
                value="Witch of Woe",
                display_type=None,
            ),
            Attribute(trait_type="Sun Sign", value="Taurus", display_type=None),
            Attribute(trait_type="Moon Sign", value="Aquarius", display_type=None),
            Attribute(trait_type="Rising Sign", value="Capricorn", display_type=None),
            Attribute(trait_type="Will", value="9", display_type="number"),
            Attribute(trait_type="Wisdom", value="9", display_type="number"),
            Attribute(trait_type="Wonder", value="9", display_type="number"),
            Attribute(trait_type="Woe", value="10", display_type="number"),
            Attribute(trait_type="Wit", value="9", display_type="number"),
            Attribute(trait_type="Wiles", value="9", display_type="number"),
        ],
        name="nyx",
        description="You are a WITCH of the highest order. You are borne of chaos that gives the night shape. Your magic spawns from primordial darkness. You are called oracle by those wise enough to listen. ALL THEOLOGY STEMS FROM THE TERROR OF THE FIRMAMENT!",
        mime_type="application/json",
        image=MediaDetails(
            size=3095,
            sha256=None,
            uri="https://cryptocoven.s3.amazonaws.com/nyx.png",
            mime_type="application/json",
        ),
        content=None,
        additional_fields=[
            MetadataField(
                field_name="external_url",
                type=MetadataFieldType.TEXT,
                description="This is the URL that will appear below the asset's image on OpenSea and will allow users to leave OpenSea and view the item on your site.",
                value="https://www.cryptocoven.xyz/witches/1",
            ),
            MetadataField(
                field_name="background_color",
                type=MetadataFieldType.TEXT,
                description="Background color of the item on OpenSea. Must be a six-character hexadecimal without a pre-pended #.",
                value="",
            ),
        ],
    )
```

In addition to testing your parser, you'll need to verify that the parser has been registered and added to the pipeline correctly. The tests in `tests/metadata/registries/test_parser_registry.py` should break if they are not modified to include your new parser class.

---

## OpenSea Schema Code

View the full source code for the OpenSea schema parser [here.](https://github.com/ourzora/offchain/blob/main/offchain/metadata/parsers/schema/opensea.py)
