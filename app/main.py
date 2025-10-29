from fastapi import FastAPI,Depends,HTTPException,status
from app.database import create_db_and_tables,get_session
from app.models import Todo,TodoCreate,TodoUpdate,User,UserCreate   
from sqlmodel import Session,select
from typing import List
from fastapi.security import OAuth2PasswordRequestForm
from app.auth import authenticate_user_db,get_current_user,get_password_hash,create_access_token
import re

app=FastAPI(title="Todo API")

@app.on_event("startup")
def on_start_up():
    create_db_and_tables()

# Normalize username: trim, lowercase, replace spaces with underscore
def normalize_username(raw: str) -> str:
    return raw.strip().lower().replace(" ", "_")

# Username must match this: lowercase letters, digits, underscore only
USERNAME_REGEX = re.compile(r"^[a-z0-9_]+$")

def validate_username_format(username: str) -> None:
    """
    Raises HTTPException(400) if username invalid.
    """
    if not USERNAME_REGEX.match(username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username may contain only lowercase letters, digits and underscore (_). "
                   "No spaces or special characters allowed."
        )

# Password rules: min_length, at least one digit, at least one uppercase letter, at least one lowercase letter
def validate_password_strength(password: str, min_length: int = 8) -> None:
    errors = []
    if len(password) < min_length:
        errors.append(f"at least {min_length} characters")
    if not re.search(r"\d", password):
        errors.append("at least one digit")
    if not re.search(r"[A-Z]", password):
        errors.append("at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        errors.append("at least one lowercase letter")

    if errors:
        # Build a single readable message
        msg = "Password must contain " + ", ".join(errors) + "."
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

# ----------------------------
# User registration
# ----------------------------
@app.post("/register", status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, session: Session = Depends(get_session)):
    """
    Register new user:
      - normalize username
      - validate username format
      - check uniqueness (case-insensitive because usernames are stored normalized)
      - validate password strength
      - store hashed password
    """
    # 1) Normalize username
    normalized = normalize_username(user_in.username)

    # 2) Validate username format
    validate_username_format(normalized)


    # 3) Check uniqueness (username stored normalized, so equality works)
    statement = select(User).where(User.username == normalized)
    if session.exec(statement).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")

    # 4) Validate password strength
    validate_password_strength(user_in.password)

    #5) create user
    hashed = get_password_hash(user_in.password)
    user = User(username=normalized, hashed_password=hashed)
    session.add(user)
    session.commit()
    session.refresh(user)

    # 6) Return minimal info
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

#date , notification in the todo and title should be managed 
#background scheduler
#username












#asyncronous 
#multi threading