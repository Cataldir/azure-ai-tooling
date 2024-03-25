"""
This Python module defines classes and methods for generating and handling queries using Azure OpenAI Service. 
It provides an abstract base class, `PromptGenerator`, which sets up the foundation for query generation and 
response handling, and a concrete implementation, `QueryGenerator`, which is specifically tailored for generating 
database queries. The module is designed to be utilized in applications that interact with Azure's AI services 
to perform tasks like database querying, processing natural language inputs, and other AI-driven operations.

Classes:
    PromptGenerator: An abstract base class that serves as a template for generating queries using Azure OpenAI 
    Service. It establishes essential properties and methods that must be implemented by its subclasses.

    QueryGenerator: A concrete implementation of PromptGenerator that specializes in creating database queries. 
    It overrides the abstract methods of its parent class to provide specific functionalities related to database 
    querying.

The module makes use of the `httpx` library for asynchronous HTTP requests and employs Azure Log Handler for logging. 
It also demonstrates best practices in async programming, error handling, and interaction with external AI services.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
import logging
from string import Template
from typing import Dict, List, Optional

import httpx
from opencensus.ext.azure.log_exporter import AzureLogHandler

from .schemas import AzureAIMessage, AzureAIRequest
from .system_message import DEFAULT_SYSTEM_MESSAGE


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class PromptGenerator(ABC):
    """
    _summary_: Abstract base class representing a query generator using Azure OpenAI Service.
    This class provides the foundational methods and properties for generating queries
    and handling responses from the Azure OpenAI Service.
    """

    def __init__(
        self,
        aoai_url: str,
        aoai_key: str,
        az_monitor: Optional[str] = None,
    ) -> None:
        """
        Initialize the PromptGenerator with Azure OpenAI Service URL, access key, and optional
        Azure Monitor connection string for logging.

        Args:
            aoai_url (str): The URL endpoint for the Azure OpenAI Service.
            aoai_key (str): Access key for Azure OpenAI Service authentication.
            az_monitor (Optional[str]): Connection string for Azure Monitor, used for logging.
        """
        self.aoai_url = aoai_url
        self.aoai_key = aoai_key
        self.__system_message: str = DEFAULT_SYSTEM_MESSAGE
        self.http_client = httpx.AsyncClient(timeout=300)
        if az_monitor:
            logger.addHandler(AzureLogHandler(connection_string=az_monitor))

    @property
    def headers(self):
        """
        Property that returns the standard headers required for Azure OpenAI Service requests,
        including Content-Type and Authorization headers.

        Returns:
            dict: A dictionary containing the necessary HTTP headers.
        """
        return {
            "Content-Type": "application/json",
            "api-key": self.aoai_key,
        }

    @property
    def system_message(self) -> str:
        """
        Property getter for the system message to be used in Azure OpenAI Service requests.

        Returns:
            str: The current system message.
        """
        return self.__system_message

    @system_message.setter
    def system_message(self, message: str) -> None:
        """
        Property setter for updating the system message.

        Args:
            message (str): The new system message to set.
        """
        self.__system_message = message

    @system_message.deleter
    def system_message(self):
        """
        Property deleter for resetting the system message to its default value.
        """
        self.__system_message = DEFAULT_SYSTEM_MESSAGE

    async def close(self):
        """
        Asynchronously close the HTTP client connection.
        """
        await self.http_client.aclose()

    async def __request_url(self, url, method, data=None):
        """
        Asynchronous private method to make an HTTP request using the specified URL,
        method, and optional data payload.

        Args:
            url (str): The URL endpoint to send the request to.
            method (str): The HTTP method to use for the request.
            data (Optional): The data payload to send with the request, if any.

        Returns:
            dict: The JSON response from the request.

        Raises:
            HTTPStatusError: If the response status code indicates an error.
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

    @abstractmethod
    async def prepare_request(
        self,
        prompt: str,
        query_type: str,
        db_params: Dict[str, str | List[str]],
        programming_language: Optional[str] = None,
    ) -> Dict[str, str]:

        """
        Abstract method to be implemented by subclasses, preparing the request to Azure OpenAI Service.
        Constructs the query request based on given parameters.

        Args:
            prompt (str): The prompt text to generate the query.
            query_type (str): The type of query to generate.
            db_params (Dict[str, Union[str, List[str]]]): Parameters relevant to the database query.
            programming_language (Optional[str]): Optional programming language for the query.

        Returns:
            Dict[str, str]: The prepared prompt request as a dictionary.
        """

    async def send_request(
        self,
        prompt: str,
        prompt_type: str,
        db_params: Dict[str, str | List[str]],
        parameters: Dict[str, str | float | int],
        programming_language: Optional[str] = None,
    ):
        """
        Asynchronously send a request to the Azure OpenAI Service using the provided parameters.
        Constructs and sends the prompt request and processes the response.

        Args:
            prompt (str): The prompt text to generate the prompt.
            prompt_type (str): The type of prompt to generate.
            db_params (Dict[str, Union[str, List[str]]]): Parameters relevant to the database query.
            parameters (Dict[str, Union[str, float, int]]): Additional parameters for the request.
            programming_language (Optional[str]): Optional programming language for the prompt.

        Returns:
            str: The result of the prompt from the Azure OpenAI Service.
        """

        prompt_request: Dict[str, str] = await self.prepare_request(
            prompt, prompt_type, db_params, programming_language
        )

        messages: List[AzureAIMessage] = [
            AzureAIMessage(
                role="system",
                content=[{"type": "text", "text": self.system_message}],
            ),
            AzureAIMessage(
                role="user",
                content=[{"type": "text", "text": prompt_request}],
            ),
        ]

        logger.debug("Sending query to Azure OpenAI Service. Messages: %s", messages)

        data = AzureAIRequest(
            messages=messages,
            temperature=float(parameters.get("temperature", 0.7)),
            top_p=float(parameters.get("top_p", 0.95)),
            max_tokens=int(parameters.get("max_tokens", 2000)),
        )

        logger.debug("Sending data to Azure OpenAI Service. Data: %s", data)

        response = await self.__request_url(
            method="get",
            url=self.aoai_url,
            data=data.model_dump()
        )

        logger.info(
            "Query successfully generated. Resources used: %s",
            {
                "model": response.get("model", ""),
                **response.get("usage", {}),
            },
        )

        result = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        return result


class QueryGenerator(PromptGenerator):
    """
    A concrete implementation of the PromptGenerator, tailored for generating database
    queries. This class implements the abstract method prepare_request to construct database
    queries based on given parameters.
    """

    async def prepare_request(
        self,
        prompt: str,
        query_type: str,
        db_params: Dict[str, str | List[str]],
        programming_language: Optional[str] = None,
    ):
        """
        Asynchronously prepares a database query request using the provided parameters. This method
        formats a query string that is tailored to interact with Azure OpenAI Service by substituting
        placeholders in a template with the actual values from the arguments. It handles various
        database-related parameters to generate a meaningful and contextually relevant query based on
        the prompt and type of query requested.

        Args:
            prompt (str): The base prompt text that forms the foundation of the query.
            query_type (str): Specifies the type of query to generate, influencing the structure of the query.
            db_params (Dict[str, Union[str, List[str]]]): A dictionary containing parameters related to the
                database query, such as database name, table name, and fields. These parameters are used to
                dynamically construct the query based on database-specific requirements.
            programming_language (Optional[str]): An optional parameter that specifies the programming language
                context for the query. This can be used to tailor the query for specific programming environments
                or syntaxes.

        Returns:
            str: A fully constructed query string ready to be sent to the Azure OpenAI Service. This string is
                formatted based on the provided prompt, query type, database parameters, and optional programming
                language.

        Raises:
            ValueError: If essential database parameters like database name or table name are missing
                in `db_params`.
        """

        query_request = "$prompt using $query_type."

        if not all(key in db_params for key in ["database_name", "table_name"]):
            logger.error(
                "Could not find database_name and table_name in db_params. Found: %s",
                set(db_params.keys()),
            )
            raise ValueError("The database name and table name are required to generate a query.")

        query_request += " The database name is $database_name, the table is $table_name"

        match db_params.get("fields", None):
            case str():
                query_request += " and the field is $field."
            case list():
                query_request += " and the fields are $fields."
            case _:
                logger.error(
                    "Could not find fields. Found: %s",
                    type(db_params.get("fields", None)),
                )

        if programming_language:
            query_request += " The programming language is $programming_language."

        query_request = Template(query_request).safe_substitute(
            prompt=prompt,
            query_type=query_type,
            programming_language=programming_language,
            **db_params,
        )
        return query_request
