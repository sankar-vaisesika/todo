from fastapi import FastAPI,Depends,HTTPException,status
from app.database import create_db_and_tables,get_session
from app.models import Todo,TodoCreate,TodoUpdate,User,UserCreate   
from sqlmodel import Session,select
from typing import List
from fastapi.security import OAuth2PasswordRequestForm
from app.auth import authenticate_user_db,get_current_user,get_password_hash,create_access_token


app=FastAPI(title="Todo API")

@app.on_event("startup")
def on_start_up():
    create_db_and_tables()



# ----------------------------
# User registration
# ----------------------------
@app.post("/register", status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, session: Session = Depends(get_session)):
    # check if username already exists
    statement = select(User).where(User.username == user_in.username)
    if session.exec(statement).first():
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed = get_password_hash(user_in.password)
    user = User(username=user_in.username, hashed_password=hashed)
    session.add(user)
    session.commit()
    session.refresh(user)
    return {"id": user.id, "username": user.username}

# ----------------------------
# Token / login
# ----------------------------


@app.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    user = authenticate_user_db(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")

    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# ----------------------------
# CREATE TODO (owner is current user)
# ----------------------------
@app.post("/todos/", response_model=Todo, status_code=status.HTTP_201_CREATED)
def create_todo(todo_in: TodoCreate, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)) -> Todo:
    todo = Todo.from_orm(todo_in)
    todo.owner_id = current_user.id
    session.add(todo)
    session.commit()
    session.refresh(todo)
    return todo



# ----------------------------
# READ ALL TODOS for current user
# ----------------------------

@app.get("/todos/",response_model=List[Todo])
def list_todos(session:Session=Depends(get_session),current_user:User=Depends(get_current_user))->List[Todo]:
    '''
    Return all Todo records
    '''
    statement=select(Todo).where(Todo.owner_id==current_user.id)
    results=session.exec(statement).all()
    return results

# ----------------------------
# READ a single todo (only if owned by current user)
# ----------------------------

@app.get("/todos/{todo_id}",response_model=Todo)
def get_todo(todo_id:int,session:Session=Depends(get_session),current_user:User=Depends(get_current_user))->Todo:
    """
    Return single Todo by primary key id.
    """
    todo=session.get(Todo,todo_id)

    if not todo or todo.owner_id!=current_user.id:
        raise HTTPException(status_code=404,detail="Todo not found")
    
    return todo

# ----------------------------
# PARIAL UPDATE a single todo-only owner
# ----------------------------
@app.patch("/todos/{todo_id}",response_model=Todo)
def partial_update(todo_id:int,todo_in:TodoUpdate,session:Session=Depends(get_session),current_user: User = Depends(get_current_user))->Todo:
    todo=session.get(Todo,todo_id)
    if not todo or todo.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Todo not found")
    
    data=todo_in.dict(exclude_unset=True)
    for k,v in data.items():
        setattr(todo,k,v)
    session.add(todo)
    session.commit()
    session.refresh(todo)
    return todo

# ----------------------------
# FULL UPDATE a single todo -only owner
# ----------------------------

@app.put("/todos/{todo_id}",response_model=Todo)
def replace_todo(todo_id:int,todo_in:TodoCreate,session:Session=Depends(get_session),current_user:User=Depends(get_current_user)):

    todo = session.get(Todo, todo_id)
    if not todo or todo.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Todo not found")

    todo.title = todo_in.title
    todo.description = todo_in.description
    todo.completed = todo_in.completed

    session.add(todo)
    session.commit()
    session.refresh(todo)
    return todo


# ----------------------------
# DELETE a single todo -only owner
# ----------------------------

@app.delete("/todos/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(todo_id: int, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    todo = session.get(Todo, todo_id)
    if not todo or todo.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Todo not found")

    session.delete(todo)
    session.commit()
    return None

#asyncronous 
#multi threading