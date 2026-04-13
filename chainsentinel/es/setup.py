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
        try:
            exists = await client.indices.exists(index=index_name)
            if exists:
                continue
        except Exception as e:
            # If exists check fails, assume index exists and continue
            print(f"[Setup] Warning: Could not check if {index_name} exists: {e}")
            continue

        try:
            with open(mapping_path) as f:
                body = json.load(f)
            await client.indices.create(index=index_name, body=body)
            print(f"[Setup] Created index {index_name}")
        except Exception as e:
            # If index creation fails, it might already exist - log and continue
            print(f"[Setup] Warning: Could not create {index_name}: {e}")


async def teardown_elasticsearch(client):
    """Delete forensic indices. Used in testing only."""
    for index_name in INDICES:
        if await client.indices.exists(index=index_name):
            await client.indices.delete(index=index_name)
