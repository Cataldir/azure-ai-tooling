import uuid
from typing import Any, List, Literal

from inspect import isfunction
from datetime import datetime
from pydantic import BaseModel, validator

from azure.search.documents.indexes.models import SearchFieldDataType
from faker import Faker


VALID_TYPES = [
    getattr(SearchFieldDataType, item)
    for item in SearchFieldDataType.__dict__
    if all(('__' not in item, not isfunction(getattr(SearchFieldDataType, item))))
]


class BaseField(BaseModel):
    name: str
    type: str

    @validator('type')
    def check_ai_search_compliant(cls, value: str):
        if value not in VALID_TYPES:
            raise ValueError(f"Field type {value} is not valid for Azure Search.")
        return value


class BaseSchema(BaseModel):
    fields: List[BaseField]
    name: str
    type: str


class FieldFactory:
    @classmethod
    def generate_id(cls):
        return str(uuid.uuid4())

    @classmethod
    def generate_name(cls):
        return Faker().name()

    @classmethod
    def generate_hobbies(cls):
        return Faker().words(nb=1)

    @classmethod
    def generate_age(cls):
        return Faker().random_int(1940, 2023)

    @classmethod
    def generate_birthday(cls):
        return Faker().date_of_birth(
            tzinfo=None,
            minimum_age=18,
            maximum_age=80
        )
