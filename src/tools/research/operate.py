import concurrent.futures
import json
import logging
import re
import string
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from azure.storage.blob import BlobClient, BlobServiceClient
from langchain.schema import Document
from langchain_community.document_loaders import AsyncHtmlLoader
from langchain_community.document_transformers import (
    BeautifulSoupTransformer,
)
from langchain_community.utilities import BingSearchAPIWrapper

from .schemas import SourceEngineSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class SearchEngine:

    def __init__(
        self,
        schema: SourceEngineSchema,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.schema = schema
        self.data = data

    def clean_text(self, text: Document) -> Tuple:
        """Cleans text from special characters."""
        content = text.page_content
        cleaned_text: str = (
            content.replace("\n", " ")
            .replace("\r", " ")
            .replace("\t", " ")
        )
        list_text: list[str | Any] = re.split(r"\W+", cleaned_text)
        table: dict[int, int | None] = str.maketrans(
            "", "", string.punctuation
        )
        stripped: list[str | Any] = [w.translate(table) for w in list_text]
        cleaned_text: str = " ".join([w for w in stripped])
        if "page" in text.metadata:
            r_key = text.metadata.get("page")
        else:
            r_key = text.metadata.get("source")
        return str(r_key), stripped

    def __get_website_text(self, url):
        """Extracts text from a given website URL."""
        website_data = {}
        try:
            loader = AsyncHtmlLoader(url)
            docs = loader.load()
            bs_transformer = BeautifulSoupTransformer()
            pages = bs_transformer.transform_documents(
                docs,
                tags_to_extract=["p", "h1", "h2", "h3", "h4", "h5", "h6"],
            )
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = [
                    executor.submit(self.clean_text, page)
                    for page in pages
                ]
                for future in concurrent.futures.as_completed(futures):
                    website_data[future.result()[0]] = future.result()[1]
            return website_data
        except Exception as exc:
            logger.error(
                "Error occurred while fetching website content: %s",
                str(exc),
            )
            return {}

    def __upload_to_blob(
        self, connect_str: str, container_name: str, blob_name: str
    ) -> None:
        try:
            blob_service_client: BlobServiceClient = (
                BlobServiceClient.from_connection_string(connect_str)
            )
            blob_client: BlobClient = blob_service_client.get_blob_client(
                container=container_name, blob=blob_name
            )
            blob_client.upload_blob(json.dumps(self.data))
        except Exception as e:
            logger.error(
                "Error occurred while uploading to Azure Blob Storage: %s",
                str(e),
            )
            raise e

    def retrieve_data(self) -> List[Dict[str, str]]:
        search = BingSearchAPIWrapper(
            bing_subscription_key=self.schema.origin.get("bing", {}).get(
                "subscription-key", ""
            ),
            bing_search_url=self.schema.origin.get("bing", {}).get(
                "endpoint", ""
            ),
        )
        query_params = self.schema.origin.get("bing", None)
        topic = self.schema.origin.get("topic", None)
        if query_params:
            results = search.results(topic, query_params.get("queries"))
        else:
            results = search.results(topic)
        website_data = {
            key: value
            for result in results
            for key, value in self.__get_website_text(
                result["link"]
            ).items()
        }
        upload_data = []
        for key, value in website_data.items():
            upload_data.append(
                {
                    "id": str(uuid.uuid4()),
                    "website": key,
                    "content": " ".join(value),
                }
            )
        self.data = upload_data
        return upload_data

    def post_data(self) -> None:
        """Uploads data to Azure Blob Storage."""

        container_name: str = self.schema.destination.get(
            "blob-container", ""
        )
        connect_str: str = self.schema.destination.get(
            "blob-connection-string", ""
        )
        blob_name = f"research-data-{time.time()}.json"
        if any((container_name == "", connect_str == "")):
            raise AttributeError("You must define destination parameters.")
        self.__upload_to_blob(connect_str, container_name, blob_name)
