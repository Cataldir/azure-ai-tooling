from __future__ import annotations

import logging
from typing import Optional

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes.aio import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchableField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


async def create_or_update_search_index(
    endpoint: str,
    api_key: str,
    index_name: Optional[str] = "some-search-index",
):

    credential = AzureKeyCredential(api_key)
    client = SearchIndexClient(endpoint=endpoint, credential=credential)
    index = SearchIndex(
        name=index_name,
        fields=[
            SimpleField(
                name="id", type=SearchFieldDataType.String, key=True
            ),
            SearchableField(
                name="website",
                type=SearchFieldDataType.String,
                filterable=True,
                sortable=True,
            ),
            SearchableField(
                name="content",
                type=SearchFieldDataType.String,
                filterable=True,
                sortable=True,
            ),
        ],
    )
    try:
        index = await client.create_or_update_index(index=index)
    except Exception as exc:
        logger.error("Could not create index. Error: %s", exc)
        return None
    finally:
        await client.close()
    return index
