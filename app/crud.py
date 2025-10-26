from sqlmodel import select,Session
from app.models import Todo

def create_todo(session:Session,todo:Todo)->Todo:
    session.add(todo)
    session.commit()
    session.refresh(todo)
    return todo