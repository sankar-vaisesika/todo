from typing import Optional
from sqlmodel import SQLModel,Field
from datetime import datetime


# ------------------------------
# Base model (common structure)
# ------------------------------
class TodoBase(SQLModel):
    # These are the fields that will come from the user when creating a Todo item.

    title: str                              # Title of the task (required)
    description: Optional[str] = None        # Description (optional field)
    completed: bool = False                  # Task status, default is False (not completed)

# ------------------------------
# Database model
# ------------------------------
class Todo(TodoBase, table=True):
    """
    This class represents the actual database table.
    It inherits all fields from TodoBase (title, description, completed),
    and adds database-specific fields such as id and created_at.
    """

    # Primary key column (automatically increments)
    # Optional[int] means this can be None initially (before inserting into DB)
    id: Optional[int] = Field(default=None, primary_key=True)
  
    # Stores the timestamp when the record is created
    # 'default_factory' means: call this function (datetime.utcnow)
    # every time a new record is created to generate the default value automatically.
    #
    # Example:
    # When you create a new Todo without specifying created_at,
    # In Django, this behaves like `models.DateTimeField(auto_now_add=True)`
    created_at: datetime = Field(default_factory=datetime.utcnow)