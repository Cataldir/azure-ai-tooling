from typing import Any, Dict, List

from pydantic import BaseModel

CONTENT_TYPE = List[Dict[str, str] | Dict[str, Dict[str, str]]]


class AzureLogHandler(BaseModel):
    connection_string: str


class SourceEngineSchema(BaseModel):
    origin: Dict[str, Any]
    destination: Dict[str, Any]
