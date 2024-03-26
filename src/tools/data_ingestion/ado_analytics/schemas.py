from typing import Optional, List

from pydantic import BaseModel

from .custom_schemas import AzureDevOpsCustomSchema


class AzureDevOpsCommentSchema(BaseModel):
    id: int
    text: str
    createdBy: str
    createdDate: str


class AzureDevOpsCommentsSchema(BaseModel):
    totalCount: int
    count: int
    comments: Optional[List[AzureDevOpsCommentSchema]]


class AzureDevOpsSystemSchema(BaseModel):
    title: str
    state: str
    changed_date: str
    work_item_type: str
    description: Optional[str] = None
    reason: Optional[str] = None
    assigned_to: Optional[str] = None


class AzureDevOpsWorkItemSchema(BaseModel):
    id: str
    system: AzureDevOpsSystemSchema
    custom: Optional[AzureDevOpsCustomSchema] = None
    comments: Optional[AzureDevOpsCommentsSchema] = None
