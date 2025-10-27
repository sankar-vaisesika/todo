from fastapi import FastAPI,Depends,HTTPException,status
from app.database import create_db_and_tables,get_session
from app.models import Todo,TodoBase,TodoCreate,TodoUpdate
from sqlmodel import Session,select
from typing import List

app=FastAPI(title="Todo API")

@app.on_event("startup")
def on_start_up():
    create_db_and_tables()


# ----------------------------
# CREATE TODO
# ----------------------------

@app.post("/todos/",response_model=Todo,status_code=status.HTTP_201_CREATED)
def create_todo(todo_in:TodoCreate,session:Session=Depends(get_session))-> Todo:
    """
    This function receives:
      - todo: the new Todo object from the client (title, description, etc.)
      - session: the database session (injected automatically using Depends)
    """
    todo=Todo.from_orm(todo_in) #build DB object from input
    session.add(todo)
    session.commit()
    session.refresh(todo)
    return todo

# ----------------------------
# READ ALL
# ----------------------------

@app.get("/todos/",response_model=List[Todo])
def list_todos(session:Session=Depends(get_session))->List[Todo]:
    '''
    Return all Todo records
    '''
    results=session.exec(select(Todo)).all()
    return results

# ----------------------------
# READ a single todo
# ----------------------------

@app.get("/todos/{todo_id}",response_model=Todo)
def get_todo(todo_id:int,session:Session=Depends(get_session))->Todo:
    """
    Return single Todo by primary key id.
    """
    todo=session.get(Todo,todo_id)

    if not todo:
        raise HTTPException(status_code=404,detail="Todo not found")
    
    return todo

# ----------------------------
# PARIAL UPDATE a single todo
# ----------------------------
@app.patch("/todos/{todo_id}",response_model=Todo)
def partial_update(todo_id:int,todo_in:TodoUpdate,session:Session=Depends(get_session))->Todo:
    todo_obj=session.get(Todo,todo_id)
    if not todo_obj:
        raise HTTPException(status_code=404,detail="Todo not found")
    
    data=todo_in.dict(exclude_unset=True)
    for k,v in data.items():
        setattr(todo_obj,k,v)
    session.add(todo_obj)
    session.commit()
    session.refresh(todo_obj)
    return todo_obj

# ----------------------------
# UPDATE a single todo
# ----------------------------

@app.put("/todos/{todo_id}",response_model=Todo)
def replace_todo(todo_id:int,todo_in:TodoCreate,session:Session=Depends(get_session)):

    todo_obj=session.get(Todo,todo_id)

    if not todo_obj:
        raise HTTPException(status_code=404,detail="Todo not found")
    
    todo_obj.title=todo_in.title
    todo_obj.description=todo_in.description
    todo_obj.completed=todo_in.completed

    session.add(todo_obj)
    session.commit()
    session.refresh(todo_obj)
    return todo_obj


# ----------------------------
# DELETE a single todo
# ----------------------------

@app.delete("/todos/{todo_id}",status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(todo_id:int,session:Session=Depends(get_session)):
    todo_obj=session.get(Todo,todo_id)
    if not todo_obj:
        raise HTTPException(status_code=404,detail="Todo not found")
    
    session.delete(todo_obj)
    session.commit()

    return None

#asyncronous 
#multi threading