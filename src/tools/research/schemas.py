from typing import List, Dict, Literal, Any

from pydantic import BaseModel


CONTENT_TYPE = List[Dict[str, str] | Dict[str, Dict[str, str]]]


class AzureAIMessage(BaseModel):
    role: Literal['system', 'user']
    content: CONTENT_TYPE


class AzureAIRequest(BaseModel):
    messages: List[AzureAIMessage]
    temperature: float
    top_p: float
    max_tokens: int


class AzureLogHandler(BaseModel):
    connection_string: str


class SourceEngineSchema(BaseModel):
    origin: Dict[str, Any]
    destination: Dict[str, Any]
