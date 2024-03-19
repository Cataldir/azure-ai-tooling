from __future__ import annotations

import os
from typing import Optional, Dict, List
from string import Template
import logging

import httpx

from opencensus.ext.azure.log_exporter import AzureLogHandler

from .schemas import AzureAIMessage, AzureAIRequest


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class QueryGenerator:
    """
    _summary_: This class is a query generator using Azure OpenAI Service.
    """
    def __init__(self, aoai_url: str, aoai_key: str, system_message: Optional[str] = None, az_monitor: Optional[str] = None) -> None:
        self.aoai_url = aoai_url
        self.aoai_headers = {
            "Content-Type": "application/json",
            "api-key": aoai_key
        }
        self.system_message = system_message or """
            You are a data engineer assistant.\n
            In your prompts, you will receive semantic requests to parse into queries for different engines.\n
            Your role is to translate the messages into the respective query system.\n
            Never include the description of the language, execution code, neither any kind of markdown.\n
            \n-----------------\n
            EXAMPLE REQUEST:\n
            Retrieve the information from all users that starts with 'ricar' using SQL. The database name is 'users' and the field is 'username'.\n
            EXAMPLE RESPONSE:\n
            SELECT * FROM users WHERE username LIKE 'ricar%';
            \n-----------------\n
            EXAMPLE REQUEST:\n
            Retrieve the information from all users that starts with 'ricar' using SPARK for Python. The database name is 'users' and the field is 'username' or 'first_name'.\n
            EXAMPLE RESPONSE:\n
            users.filter(users.username.startswith('ricar'))
        """
        if az_monitor:
            logger.addHandler(AzureLogHandler(connection_string=az_monitor))

    async def send_query(
            self,
            prompt: str,
            query_type: str,
            db_params: Dict[str, str | List[str]],
            parameters: Dict[str, str | float | int],
            programming_language: Optional[str] = None,
        ):

        query_request = "$prompt using $query_type."

        if not all(key in db_params for key in ['database_name', 'table_name']):
            logger.error("Could not find database_name and table_name in db_params. Found: %s", set(db_params.keys()))
            raise ValueError("The database name and table name are required to generate a query.")

        query_request += " The database name is $database_name, the table is $table_name"

        match db_params.get('fields', None):
            case str():
                query_request += " and the field is $field."
            case list():
                query_request += " and the fields are $fields."
            case _:
                logger.error("Could not find fields. Found: %s", type(db_params.get('fields', None)))

        if programming_language:
            query_request += " The programming language is $programming_language."

        query_request = Template(query_request).safe_substitute(
            prompt=prompt,
            query_type=query_type,
            programming_language=programming_language,
            **db_params
        )

        messages = [
            AzureAIMessage(
                role="system",
                content=[{"type": "text", "text": self.system_message}]
            ),
            AzureAIMessage(
                role="user",
                content=[{"type": "text", "text": query_request}]
            )
        ]

        logger.debug("Sending query to Azure OpenAI Service. Messages: %s", messages)

        data = AzureAIRequest(
            messages = messages,
            temperature=float(parameters.get('temperature', 0.7)),
            top_p=float(parameters.get('top_p', 0.95)),
            max_tokens=int(parameters.get('max_tokens', 2000))
        ).model_dump()

        logger.debug("Sending data to Azure OpenAI Service. Data: %s", data)

        async with httpx.AsyncClient() as client:
            response = await client.post(self.aoai_url, headers=self.aoai_headers, json=data)

        try:
            response.raise_for_status()
            completion = dict(response.json())
            logger.info(
                "Query successfully generated. Resources used: %s",
                {'model': completion.get('model', ''), **completion.get('usage', {})}
            )
            result = completion.get('choices', [{}])[0].get('message', {}).get('content', '')
            return result

        except httpx.RequestError as exc:
            logger.error("An error occurred while sending the request. %s", exc)
            return {"error": exc}
