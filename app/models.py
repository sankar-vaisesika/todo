from typing import Optional,List
from sqlmodel import SQLModel,Field,Relationship
from datetime import datetime

# -------------------------
# User models
# -------------------------

class UserBase(SQLModel):
    username:str=Field(unique=True,nullable=False,max_length=20,description="Unique username")

class UserCreate(UserBase):
    password:str

class User(UserBase,table=True):
    id:Optional[int]=Field(default=None,primary_key=True)
    hashed_password:str
    # Relationship: one user -> many todos
    todos: List["Todo"] = Relationship(back_populates="owner")

class TodoBase(SQLModel):
    title:str=Field(max_length=100)
    description:Optional[str]=Field(None,max_length=200)
    completed:bool=Field(False)


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

    # Owner foreign key and relationship
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id")
    owner: Optional[User] = Relationship(back_populates="todos")