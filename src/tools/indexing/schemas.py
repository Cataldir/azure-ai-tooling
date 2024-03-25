
from inspect import isfunction
from typing import Any, Dict, List

from azure.search.documents.indexes.models import SearchFieldDataType
from pydantic import BaseModel, validator


VALID_TYPES = [
    getattr(SearchFieldDataType, item)
    for item in SearchFieldDataType.__dict__
    if all(
        (
            "__" not in item,
            not isfunction(getattr(SearchFieldDataType, item)),
        )
    )
]


class BaseField(BaseModel):
    name: str
    field_type: str
    params: Dict[str, Any]

    @validator("field_type")
    def check_ai_search_compliant(cls, value: str) -> str:
        if value not in VALID_TYPES:
            raise ValueError(
                f"Field type {value} is not valid for Azure Search."
            )
        return value
