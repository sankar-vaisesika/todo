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
    is_admin:Optional[bool]=Field(default=False)

class User(UserBase,table=True):
    id:Optional[int]=Field(default=None,primary_key=True)
    hashed_password:str
    is_admin:bool
    # Relationship: one user -> many todos
    todos: List["Todo"] = Relationship(back_populates="owner")
    notifications:List["Notification"]=Relationship(back_populates="user")

# -------------------------
# Todo models
# -------------------------

class TodoBase(SQLModel):
    title:str=Field(max_length=100)
    description:Optional[str]=Field(None,max_length=200)
    completed:bool=Field(False)


# Model used when creating (input)
class TodoCreate(TodoBase):
    due_date:Optional[datetime]=Field(None,description="Deadline to complete the task")
    reminder_at: Optional[datetime] = Field(None, description="UTC datetime when reminder should be triggered (ISO format)")



# Model used for updates (all fields optional for PATCH-like behaviour)
class TodoUpdate(SQLModel):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    completed: Optional[bool] = None
    due_date:Optional[datetime]=None
    reminder_at: Optional[datetime] = None

# DB model / response model
class Todo(TodoBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    due_date: Optional[datetime] = Field(None, description="Deadline to complete the task")

    # Reminder fields
    reminder_at: Optional[datetime] = Field(None, description="UTC datetime for reminder")
    notified: bool = Field(False, description="True if reminder already sent")

    # Owner foreign key and relationship
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id")
    owner: Optional[User] = Relationship(back_populates="todos")


# -------------------------
# Notification model 
# -------------------------

class NotificationBase(SQLModel):
    title:str
    message:Optional[str]=None
    created_at: datetime = Field(default_factory=datetime.now)

class NotificationCreate(NotificationBase):
    todo_id:Optional[int]=None

class Notification(NotificationBase,table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    todo_id: Optional[int] = Field(default=None, foreign_key="todo.id")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    # Relationship backrefs can be added if needed
    user: Optional[User] = Relationship(back_populates="notifications")