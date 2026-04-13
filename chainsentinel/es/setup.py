import json
from pathlib import Path


MAPPINGS_DIR = Path(__file__).parent / "mappings"

INDICES = {
    "forensics-raw": MAPPINGS_DIR / "forensics-raw.json",
    "forensics": MAPPINGS_DIR / "forensics.json",
}


async def setup_elasticsearch(client):
    """Create forensic indices with strict mappings if they don't exist."""
    for index_name, mapping_path in INDICES.items():
        if await client.indices.exists(index=index_name):
            continue

        with open(mapping_path) as f:
            body = json.load(f)

        await client.indices.create(index=index_name, body=body)


async def teardown_elasticsearch(client):
    """Delete forensic indices. Used in testing only."""
    for index_name in INDICES:
        if await client.indices.exists(index=index_name):
            await client.indices.delete(index=index_name)
