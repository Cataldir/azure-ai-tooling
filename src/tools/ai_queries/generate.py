from __future__ import annotations

from typing import Optional, Dict, List, Union
from string import Template

import httpx

from .schemas import AzureAIMessage, AzureAIRequest


class QueryGenerator:
    """
    _summary_: This class is a query generator using Azure OpenAI Service.
    """
    def __init__(self, aoai_url: str, system_message: Optional[str] = None) -> None:
        self.aoai_url = aoai_url
        self.system_message = system_message or """
            You are a data engineer assistant.\n
            In your prompts, you will receive semantic requests to parse into queries for different engines.\n
            Your role is to translate the messages into the respective query system.\n
            \n-----------------\n
            EXAMPLE REQUEST:\n
            Retrieve the information all users that starts with 'ricar' using SQL. The database name is 'users' and the field is 'username'.\n
            EXAMPLE RESPONSE:\n
            SELECT * FROM users WHERE username LIKE 'ricar%';
            \n-----------------\n
            EXAMPLE REQUEST:\n
            Retrieve the information all users that starts with 'ricar' using SPARK for Python. The database name is 'users' and the field is 'username'.\n
            EXAMPLE RESPONSE:\n
            users.filter(users.username.startswith('ricar'))
        """

    async def send_query(
            self,
            prompt: str,
            query_type: str,
            db_params: Dict[str, str | List[str]],
            programming_language: Optional[str] = None,
            parameters: Optional[Dict[str, str | float | int]] = None
        ):
        # Define the headers for the HTTP request
        headers = {"Content-Type": "application/json"}
        query_request = "{$prompt} using {$query_type}."
        database_info = " The database name is {$database_name}, the table is {$table_name}"

        match type(db_params.get('fields', None)):
            case "str":
                field_info = " and the field is {$field}."
            case "list":
                field_info = " and the fields are {$fields}."
            case _:
                field_info = None

        if programming_language:
            query_request = query_request + " The programming language is {$programming_language}."

        messages = [
            AzureAIMessage(role="system", content=[{"type": "text", "text": self.system_message}]),
            AzureAIMessage(
                role="user",
                content=[{"type": "text", "text": Template(query_request).substitute(prompt=prompt, query_type=query_type, programming_language=programming_language)}]
            )
        ]

        data = AzureAIRequest(
            messages = messages,
            temperature=parameters.get('temperature', 0.7),
            top_p=parameters.get('top_p', 0.95),
            max_tokens=parameters.get('max_tokens', 2000)
        ).model_json()
        # Send the HTTP request and get the response
        response = await httpx.post(self.aoai_url, headers=headers, json=data)

        # Return the response
        return response.json()
