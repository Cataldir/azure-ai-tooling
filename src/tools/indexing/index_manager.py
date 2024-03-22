from __future__ import annotations

import logging
from typing import Optional, List

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchIndexingBufferedSender
from azure.search.documents.indexes.aio import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchFieldDataType
)

from .schemas import BaseSchema


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


async def create_or_update_search_index(
    endpoint: str,
    api_key: str,
    index_name: Optional[str] = "azure-devops-index"
):

    credential = AzureKeyCredential(api_key)
    client = SearchIndexClient(endpoint=endpoint, credential=credential)
    index = SearchIndex(
        name=index_name,
        fields=[
                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                SearchableField(name="title", type=SearchFieldDataType.String, filterable=True, sortable=True),
                SearchableField(name="work_item_type", type=SearchFieldDataType.String, filterable=True, sortable=True),
                SearchableField(name="activity_type", type=SearchFieldDataType.String, filterable=True, sortable=True),
                SearchableField(name="state", type=SearchFieldDataType.String, filterable=True, sortable=True),
                SearchableField(name="engagement_outcome", type=SearchFieldDataType.String, filterable=True, sortable=True),
                SearchableField(name="reason", type=SearchFieldDataType.String, filterable=True, sortable=True),
                SearchableField(name="assigned_to", type=SearchFieldDataType.String, filterable=True, sortable=True),
                SearchableField(name="opportunity_id", type=SearchFieldDataType.String, filterable=True, sortable=True),
                SearchableField(name="milestone_ids", type=SearchFieldDataType.String, filterable=True, sortable=True),
                SearchableField(name="changed_date", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
                SearchableField(name="gbb_specialist", type=SearchFieldDataType.String, filterable=True, sortable=True),
                SearchableField(name="gbb_tai", type=SearchFieldDataType.String, filterable=True, sortable=True),
                SearchableField(name="gbb_tapps", type=SearchFieldDataType.String, filterable=True, sortable=True),
                SearchableField(name="gbb_tml", type=SearchFieldDataType.String, filterable=True, sortable=True),
                SearchableField(name="business_impact", type=SearchFieldDataType.String, filterable=True, sortable=True),
                SearchableField(name="use_case_category", type=SearchFieldDataType.String,  filterable=True, sortable=True),
                SearchableField(name="use_case_summary", type=SearchFieldDataType.String, filterable=True, sortable=True),
                SearchableField(name="competitor", type=SearchFieldDataType.String, filterable=True, sortable=True),
                SearchableField(name="description", type=SearchFieldDataType.String, filterable=True, sortable=True),
                SearchableField(name="latest_status_detail", type=SearchFieldDataType.String, filterable=True, sortable=True),
                SearchableField(name="Comments", type=SearchFieldDataType.String, filterable=True, sortable=True)
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
    credential: AzureKeyCredential,
    data: List[BaseSchema]
):
    sender = SearchIndexingBufferedSender(
        endpoint=endpoint,
        index_name=index_name,
        credential=credential
    )

    async with sender:
        await sender.upload_documents([doc.model_dump() for doc in data])
