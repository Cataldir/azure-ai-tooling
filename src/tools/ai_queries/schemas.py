"""
This Python module is designed to define data models and structures for interacting with Azure AI services, 
specifically tailored for generating and processing requests involving natural language processing. 
It utilizes Pydantic for model validation, ensuring data integrity and type safety.

The module defines three main classes, each representing a specific data structure required to construct and 
send requests to Azure AI services. These models encapsulate data for AI-driven operations, such as text generation, 
querying, or other AI tasks. They are particularly useful for applications integrating Azure AI functionalities.

Classes:
    AzureAIMessage: Represents a message structure with a defined role (either 'system' or 'user') and content. 
    The content can be a list of dictionaries, allowing for complex and varied message formats. This class is 
    essential for constructing dialogues or interactions in an AI context.

    AzureAIRequest: Defines the structure of a request sent to Azure AI. It includes a list of AzureAIMessage 
    objects, and parameters like 'temperature', 'top_p', and 'max_tokens', which are used to control aspects 
    of the AI's response generation, such as creativity and length.

    PromptTemplate: A model representing a template for AI-driven prompts. It includes the actual prompt text, 
    the type of query, the programming language context, and database parameters. This class is useful for 
    generating context-specific AI queries, particularly in scenarios involving database interactions or 
    programming-related tasks.

Each class is defined using Pydantic, which adds automatic validation of the data fields, ensuring that the data 
passed to Azure AI services is in the correct format and adheres to the expected schema. This module is ideal for 
developers working on AI-powered applications requiring structured and validated input for Azure AI services.
"""


from typing import Dict, List, Literal, Union

from pydantic import BaseModel


CONTENT_TYPE = List[Union[Dict[str, str], Dict[str, Dict[str, str]]]]


class AzureAIMessage(BaseModel):
    role: Literal["system", "user"]
    content: CONTENT_TYPE


class AzureAIRequest(BaseModel):
    messages: List[AzureAIMessage]
    temperature: float
    top_p: float
    max_tokens: int


class PromptTemplate(BaseModel):
    prompt: str
    query_type: str
    programming_language: str
    db_params: Dict[str, str | List[str]]
