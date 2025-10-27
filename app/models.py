from typing import Optional
from sqlmodel import SQLModel,Field
from datetime import datetime


# class Todo(SQLModel, table=True):
#     id: Optional[int] = Field(default=None, primary_key=True)
#     title: str
#     description: Optional[str] = None
#     completed: bool = False
#     created_at: datetime = Field(default_factory=datetime.utcnow)

class TodoBase(SQLModel):
    title:str=Field(max_length=100)
    description:Optional[str]=Field(None,max_length=200)
    completed:Optional[bool]=None


# Model used when creating (input)
class TodoCreate(TodoBase):
    pass


# Model used for updates (all fields optional for PATCH-like behaviour)
class TodoUpdate(SQLModel):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    completed: Optional[bool] = None

# DB model / response model
class Todo(TodoBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

