import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_setup_creates_indices_if_not_exist():
    from es.setup import setup_elasticsearch

    mock_client = AsyncMock()
    mock_client.indices.exists.return_value = False

    await setup_elasticsearch(mock_client)

    assert mock_client.indices.create.call_count == 2

    calls = mock_client.indices.create.call_args_list
    index_names = [c.kwargs["index"] for c in calls]
    assert "forensics-raw" in index_names
    assert "forensics" in index_names


@pytest.mark.asyncio
async def test_setup_skips_existing_indices():
    from es.setup import setup_elasticsearch

    mock_client = AsyncMock()
    mock_client.indices.exists.return_value = True

    await setup_elasticsearch(mock_client)

    mock_client.indices.create.assert_not_called()


@pytest.mark.asyncio
async def test_setup_uses_mapping_files():
    from es.setup import setup_elasticsearch

    mock_client = AsyncMock()
    mock_client.indices.exists.return_value = False

    await setup_elasticsearch(mock_client)

    for c in mock_client.indices.create.call_args_list:
        body = c.kwargs["body"]
        assert "mappings" in body
        assert body["mappings"]["dynamic"] == "strict"
