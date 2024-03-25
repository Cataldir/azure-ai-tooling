from typing import Type, List
from pydantic import BaseModel

from .schemas import BaseField, VALID_TYPES


def type_mapping(odata_type: str):
    mapping = {
        "str": "Edm.String",
        "int": "Edm.Int64",
        "float": "Edm.Double",
        "bool": "Edm.Boolean",
        "datetime": "Edm.DateTimeOffset"
    }
    return mapping.get(odata_type, "str")


def map_pydantic_models(source_model: Type[BaseModel]) -> List[BaseField]:
    mapped_fields = []

    for field_name, field_type in source_model.__annotations__.items():
        mapped_type = type_mapping(field_type.__name__)

        params = {
            "filterable": True,
            "searchable": True,
            "sortable": True
        }

        if field_name.lower() == "id":
            params["key"] = True

        if mapped_type in VALID_TYPES:
            field = BaseField(
                name=field_name,
                field_type=mapped_type,
                params=params
            )
            mapped_fields.append(field)
        else:
            raise ValueError(f"Unsupported field type: {field_type.__name__}")

    return mapped_fields
