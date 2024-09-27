# offchain

[Documentation](https://ourzora.github.io/offchain/) | [Zora API](https://api.zora.co)

---

`offchain` is a library for parsing NFT metadata. It's used by Zora's indexer & API.
It can handle metadata of many standards (OpenSea, ZORA, Nouns), hosted in many places (ipfs, http, dataURIs),
and normalize them into a consistent format.

Our goal with this project is to democratize access to NFT metadata.

```shell
pip install offchain
```

```python
from offchain import MetadataPipeline, Token

pipeline = MetadataPipeline()
token = Token(
    collection_address="0x5180db8f5c931aae63c74266b211f580155ecac8",
    token_id=9559
)
metadata = pipeline.run([token])[0]

metadata.name               # -> 'antares the improbable'
metadata.description        # -> 'You are a WITCH who bathes in the tears of...'
metadata.standard           # -> OPENSEA_STANDARD
metadata.attributes         # -> [Attribute(trait_type='Skin Tone', ...]
metadata.image              # -> MediaDetails(size=2139693, sha256=None, uri='https://cryptocoven.s3.amazonaws.com/2048b255aa1d02045eef13cdd7100479.png', mime_type='image/png')
metadata.additional_fields  # -> [MetadataField(...), ...]
```

See [documentation](https://ourzora.github.io/offchain/) for more examples and tutorials.

## Contributing

We welcome contributions that add support for new metadata standards, new ways of retreiving metadata, and ways of normalizing them to a consistent form.
We are commited to integrating contributions to our indexer and making the results available in our API.

You should be able to contribute a new standard for metadata, and have NFTs that adhere to that metadata standard
be returned correctly from queries to `api.zora.co`. We hope this helps to foster innovation in how
NFTs are represented, where metadata is stored, and what is expressed in that metadata.

## Features

- Multiple metadata standards: represent metadata any way you wish
- Multiple transport protocols: store metadata where you want
- Composible for custom applications: only parse the standards you care about
- Future proof: extensible to new formats, locations, etc. The more gigabrain the better.

## Development

This project is developed using Python 3.9. Here's a recommended setup:

### Poetry

This project uses `poetry` for dependency management and packaging. Install poetry:

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### Setup

```bash
poetry install
```

### Pre-commit

Pre-commit runs checks to enforce coding standards on every commit

```
pip install pre-commit  # into global python path
pre-commit install
```

### Testing

```bash
poetry run python -m pytest tests/
```

### Documentation

This project uses `mkdocs` and `mkdocs-material` for documentation

```bash
poetry run mkdocs serve
```
