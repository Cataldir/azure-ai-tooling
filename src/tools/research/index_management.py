from __future__ import annotations

import logging
from typing import Optional, List, Dict

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchIndexingBufferedSender
from azure.search.documents.indexes.aio import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchFieldDataType
)


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


async def create_or_update_search_index(
    endpoint: str,
    api_key: str,
    index_name: Optional[str] = "claro-bing-search-index"
):

    credential = AzureKeyCredential(api_key)
    client = SearchIndexClient(endpoint=endpoint, credential=credential)
    index = SearchIndex(
        name=index_name,
        fields=[
                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                SearchableField(name="website", type=SearchFieldDataType.String, filterable=True, sortable=True),
                SearchableField(name="content", type=SearchFieldDataType.String, filterable=True, sortable=True)
        ]
    )
    try:
        index = await client.create_or_update_index(index=index)
    except Exception as exc:
        logger.error("Could not create index. Error: %s", exc)
        return None
    finally:
        await client.close()
    return index


async def add_data_to_index(
    endpoint: str,
    index_name: str,
    api_key: str,
    data: List[Dict[str, str]]
):
    credential = AzureKeyCredential(api_key)
    sender = SearchIndexingBufferedSender(endpoint=endpoint, index_name=index_name, credential=credential)
    try:
        async with sender:
            await sender.upload_documents(documents=data)
            await sender.flush()
    except Exception as e:
        logger.error("Failed to upload documents: %s", e)
    finally:
        await sender.close()
