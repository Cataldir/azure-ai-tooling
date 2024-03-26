"""
This module provides a comprehensive suite of functionalities for extracting, processing,
and formatting work item data from Azure DevOps. It utilizes the HTTPX library for asynchronous
HTTP requests and leverages environment variables for configuration. The module is designed
to integrate seamlessly with Azure DevOps REST API, offering efficient methods to retrieve 
work item details, comments, and apply custom formatting.

Classes:
    AzureDevOpsExtractor: A class that encapsulates methods for extracting work item information 
    from Azure DevOps, including fetching work items, their details, comments, and structuring 
    the data into predefined schemas.

Dependencies:
    asyncio: For asynchronous programming.
    base64, json, os: For data encoding, serialization, and environment variable management.
    logging: For logging purposes.
    httpx: For making asynchronous HTTP requests.
    dateutil.parser: For parsing date strings.
    dotenv: For loading environment variables.
    AzureDevOpsWorkItemSchema, AzureDevOpsCommentsSchema: Custom schemas for data representation.
    parse_work_items, parse_comments: Utility functions for parsing data.
"""

import asyncio
import base64
import json
import logging
import os
from datetime import timedelta
from typing import Any, Dict, List

import httpx
from dateutil import parser
from dotenv import load_dotenv

from .schemas import AzureDevOpsWorkItemSchema, AzureDevOpsCommentsSchema
from .ado_mapping import parse_work_items, parse_comments


logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)

load_dotenv(override=True)


class AzureDevOpsExtractor:
    """
    This class handles the extraction of work items and their details from Azure DevOps.
    It supports various operations like retrieving work items based on date, fetching details 
    and comments for each item, and applying custom parsing and formatting.
    """

    def __init__(self) -> None:
        """
        Initializes the AzureDevOpsExtractor with necessary configurations and sets up the HTTP client.
        """
        self.token = os.getenv("ADO_PERSONAL_ACCESS_TOKEN", "")
        self.base_url = os.getenv("ADO_ORGANIZATION_URL", "")
        self.project = os.getenv("ADO_TEAM_PROJECT", "")
        self.http_client = httpx.AsyncClient(timeout=300)

    @property
    def __encoded_token(self):
        """
        Encodes the Azure DevOps Personal Access Token for use in HTTP request headers.
        """
        return base64.b64encode(bytes(":" + self.token, "ascii")).decode("ascii")

    @property
    def headers(self):
        """
        Constructs and returns standard HTTP headers for Azure DevOps API requests.
        """
        return {
            "Authorization": f"Basic {self.__encoded_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def close(self):
        """
        Closes the asynchronous HTTP client session.
        """
        await self.http_client.aclose()

    async def __request_url(self, url, method, data=None):
        """
        Sends an asynchronous HTTP request to the given URL with the specified method and data.
        It handles network and HTTP status errors, with a retry mechanism for certain error scenarios.

        Args:
            url (str): The endpoint URL for the HTTP request.
            method (str): HTTP method to be used for the request.
            data (Optional[Dict]): Data payload for the request.

        Returns:
            Dict: JSON response from the HTTP request.
        """
        request_param = {
            "method": method,
            "url": url,
            "headers": self.headers,
        }
        if data:
            request_param["data"] = data
        try:
            response = await self.http_client.request(**request_param)
            response.raise_for_status()
            logger.info("Request Successful: %s", response.status_code)
            return response.json()
        except httpx.NetworkError as exc:
            logger.error("Network Error: %s. Trying Again.", str(exc))
            await asyncio.sleep(0.5)
            return await self.__request_url(url, method, data)
        except httpx.HTTPStatusError as exc:
            if response.status_code == 503:
                logger.error("Server unavailable: %s. Trying Again.", str(exc))
                await asyncio.sleep(60)
            else:
                raise exc
            logger.info("Service was unavailable. Trying again.")
            return await self.__request_url(url, method, data)

    async def get_work_items(self, process_date: str, days_length: int = 30) -> Dict[str, Any]:
        """
        Fetches a list of work items from Azure DevOps based on the provided processing date and duration.

        Args:
            process_date (str): The start date for fetching work items.
            days_length (int): Number of days from the start date to fetch work items.

        Returns:
            Dict[str, Any]: A dictionary representing the list of retrieved work items.
        """
        max_date = parser.parse(process_date) + timedelta(days=days_length)
        query = f"""
            SELECT *
            FROM workitems
            WHERE [System.TeamProject] = '{self.project}'
            AND [System.ChangedDate] >= '{process_date}'
            AND [System.ChangedDate] < '{max_date.strftime('%Y-%m-%d')}'
        """
        data = json.dumps({"query": query})
        address = "_apis/wit/wiql?api-version=7.2-preview.2"
        url = f"{self.base_url}/{self.project}/{address}"
        work_items_list = await self.__request_url(url, "post", data)
        logger.info("Work Items List retrieved: %s", str(len(work_items_list)))
        return work_items_list

    async def get_work_items_details(self, work_items_list: Dict[str, Any]) -> list[Any]:
        """
        Retrieves detailed information for each work item in the provided list.

        Args:
            work_items_list (Dict[str, Any]): A dictionary containing basic work item data.

        Returns:
            List[Dict]: A list of dictionaries, each containing detailed information about a work item.
        """
        work_items = work_items_list.get("workItems", [])
        logger.info("Work Items: %s", str(len(work_items)))
        urls = [work_item.get("url", []) for work_item in work_items]
        logger.info("Urls: %s", str(len(urls)))
        items_gather = asyncio.gather(*[self.__request_url(url, "get") for url in urls])
        list_of_items = await items_gather
        return list_of_items

    async def get_working_item_comments(self, work_item: AzureDevOpsWorkItemSchema) -> AzureDevOpsWorkItemSchema:
        """
        Fetches comments for a given work item from Azure DevOps.

        Args:
            work_item (AzureDevOpsWorkItemSchema): The work item for which comments need to be fetched.

        Returns:
            AzureDevOpsWorkItemSchema: The work item updated with comments information.
        """
        comments_url = f"_apis/wit/workItems/{work_item.id}/comments?api-version=7.2-preview.4"
        url = f"{self.base_url}/{self.project}/{comments_url}"
        work_item_comments = await self.__request_url(url, "get")
        comments = parse_comments(work_item_comments.get("comments", []))
        work_item.comments = AzureDevOpsCommentsSchema(
            totalCount=work_item_comments.get("totalCount", 0),
            count=work_item_comments.get("count", 0),
            comments=comments,
        )
        return work_item

    async def format_work_items(self, **kwargs) -> List[AzureDevOpsWorkItemSchema]:
        """
        Formats the fetched work items into structured AzureDevOpsWorkItemSchema objects.

        Args:
            **kwargs: Keyword arguments passed to the work item fetching method.

        Returns:
            List[AzureDevOpsWorkItemSchema]: A list of formatted work item objects.
        """
        items_list = await self.get_work_items(**kwargs)
        items_details = await self.get_work_items_details(items_list)
        work_items = parse_work_items(items_details)
        work_items_comments = await asyncio.gather(
            *[self.get_working_item_comments(work_item) for work_item in work_items]
        )
        await self.close()
        return work_items_comments
