from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timezone


from fastapi import FastAPI,Depends,HTTPException,status
 
from sqlmodel import Session,select
from typing import List
from fastapi.security import OAuth2PasswordRequestForm
from app.auth import authenticate_user_db,get_current_user,get_password_hash,create_access_token
from app.database import create_db_and_tables,get_session,engine
from app.models import Todo,TodoCreate,TodoUpdate,User,UserCreate,Notification
import re

app=FastAPI(title="Todo API")


import logging #logging helps to track events happening inside your app(useful for debugging and monitoring)

logger=logging.getLogger('todo_reminder') #Creates a logger named "todo_reminder".

logger.setLevel(logging.INFO)#Ensures that all messages with level INFO and above (WARNING, ERROR, etc.) will be recorded.
#This way, whenever a reminder triggers, you will see it in your server console.

# ----------------------------
# Scheduler job function
# ----------------------------

def check_and_send_reminders():
    """APScheduler job — create session locally (no Depends)."""
    """
    This job runs periodically (every minute).
    It finds todos with reminder_at <= now (UTC) and notified == False,
    creates a Notification record and marks the todo as notified.
    Replace the 'notify' action with actual email/push sending if required.
    """
    now = datetime.now()  # naive UTC for comparison with stored naive datetimes
    with Session(engine) as session:
        stmt=select(Todo).where(Todo.reminder_at!=None,Todo.reminder_at<=now,Todo.notified==False)
        due_todos=session.exec(stmt).all()
        if not due_todos:
            return
        for todo in due_todos:
            # create a notification record for the user
            message = f"Reminder: {todo.title}"
            notif = Notification(title=f"Reminder for todo #{todo.id}", message=message, todo_id=todo.id, user_id=todo.owner_id)
            session.add(notif)
            # mark todo as notified so we don't send again
            todo.notified = True
            todo.updated_at = datetime.now()
            session.add(todo)
            # Log the reminder (placeholder for sending email/push)
            logger.info(f"Reminder created for Todo id={todo.id}, owner_id={todo.owner_id}, reminder_at={todo.reminder_at}")
        session.commit()

# create and configure scheduler (global variable)
scheduler = BackgroundScheduler()
scheduler.add_job(check_and_send_reminders, "interval", seconds=60, id="todo_reminder_job", replace_existing=True)

#start scheduler on app startup and shutdown on app shutdown
@app.on_event("startup")
def start_scheduler_and_create_db():
    create_db_and_tables()        
    try:
        scheduler.start()
        logger.info("APScheduler started for reminders.")
    except Exception as e:
        logger.exception("Failed to start scheduler:%s",e)
@app.on_event("shutdown")
def shutdown_scheduler():
    scheduler.shutdown(wait=False)
    logger.info("APScheduler shutdown.")

#-----------------
#Notification endpoints
#-----------------
@app.get("/notifications", response_model=list[Notification])
def list_notifications(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    notifications = session.exec(
        select(Notification).where(Notification.user_id == current_user.id)
    ).all()
    return notifications

def normalize_username_candidate(raw: str) -> str:
    """
    Only strip leading/trailing whitespace. Do NOT change spaces internally here;
    we will reject usernames containing spaces explicitly.
    """
    return raw.strip()

# Username must match this: lowercase letters, digits, underscore only
USERNAME_REGEX = re.compile(r"^[a-z0-9_]+$")

def validate_username(username_raw: str) -> str:
    """
    Validate and return the normalized username (stripped).
    Raises HTTPException(400) if invalid.
    Rules:
      - no spaces at all
      - must be lowercase (reject if contains uppercase)
      - only a-z, 0-9 and underscore allowed
    """
    if username_raw is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username is required")
    
    candidate = normalize_username_candidate(username_raw)


    # 1) No spaces anywhere
    if " " in candidate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must not contain spaces. Use lowercase letters, digits and underscore only."
        )

    # 2) Must be lowercase (reject uppercase)
    if candidate != candidate.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be lowercase only (no uppercase letters)."
        )

    # 3) Only allowed characters
    if not USERNAME_REGEX.fullmatch(candidate):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username may contain only lowercase letters (a-z), digits (0-9) and underscore (_)."
        )

    return candidate


# -------------------------
# Password validation helpers
# -------------------------
# Define allowed special symbols (choose a small safe set)
ALLOWED_SYMBOLS = "!@$%&*()-_+="
# build regex that matches only allowed characters (letters, digits and allowed symbols)
ALLOWED_PASSWORD_RE = re.compile(rf"^[A-Za-z0-9{re.escape(ALLOWED_SYMBOLS)}]+$")


def validate_password_strength(password: str, min_length: int = 8) -> None:
    """
    Validate password:
      - minimum length (default 8)
      - at least one uppercase letter
      - at least one lowercase letter
      - at least one digit
      - at least one allowed symbol from ALLOWED_SYMBOLS
      - only characters from the allowed set are permitted
    Raises HTTPException(400) when invalid with a clear message.
    """
    if password is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password is required")
    errors = []
    if len(password) < min_length:
        errors.append(f"at least {min_length} characters")
    if not re.search(r"\d", password):
        errors.append("at least one digit")
    if not re.search(r"[A-Z]", password):
        errors.append("at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        errors.append("at least one lowercase letter")
    if not re.search(rf"[{re.escape(ALLOWED_SYMBOLS)}]", password):
        errors.append(f"at least one symbol from this set: {ALLOWED_SYMBOLS}")
    
    # ensure every character is allowed (prevent unexpected special chars)
    if not ALLOWED_PASSWORD_RE.fullmatch(password):
        errors.append(f"password contains invalid character(s). Allowed symbols: {ALLOWED_SYMBOLS}")

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
    New registration:
      - validate username (no spaces, lowercase only, allowed chars)
      - check uniqueness
      - validate password (strength and allowed chars)
      - store hashed password and return minimal info
    """
    # validate and normalize username
    normalized = validate_username(user_in.username)
    
    # uniqueness check (username stored normalized)
    statement = select(User).where(User.username == normalized)
    if session.exec(statement).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")

    # Validate password strength
    validate_password_strength(user_in.password)

    #create user
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
    existing_todo = session.exec(
    select(Todo).where(Todo.owner_id == current_user.id, Todo.title == todo_in.title)).first()
    if existing_todo:
        raise HTTPException(status_code=400, detail="You already have a todo with this title.")

    todo = Todo.from_orm(todo_in)
    todo.owner_id = current_user.id
    # optional explicit: set updated_at same as created_at now
    todo.updated_at = datetime.now()
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
# PARIAL UPDATE a single todo-only owner(PATCH)
# ----------------------------
@app.patch("/todos/{todo_id}",response_model=Todo)
def partial_update(todo_id:int,todo_in:TodoUpdate,session:Session=Depends(get_session),current_user: User = Depends(get_current_user))->Todo:
    todo=session.get(Todo,todo_id)
    if not todo or todo.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Todo not found")
    
    data=todo_in.dict(exclude_unset=True)#is a Pydantic feature used when converting a model (like a request body) into a Python dictionary.
    for k,v in data.items():
        setattr(todo,k,v)
    #update the timestamp

    todo.updated_at = datetime.now()
    session.add(todo)
    session.commit()
    session.refresh(todo)
    return todo

# ----------------------------
# FULL UPDATE a single todo -only owner(PUT)
# ----------------------------

@app.put("/todos/{todo_id}",response_model=Todo)
def replace_todo(todo_id:int,todo_in:TodoCreate,session:Session=Depends(get_session),current_user:User=Depends(get_current_user)):

    todo = session.get(Todo, todo_id)
    if not todo or todo.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Todo not found")

    todo.title = todo_in.title
    todo.description = todo_in.description
    todo.completed = todo_in.completed
    todo.due_date = todo_in.due_date
    todo.reminder_at = todo_in.reminder_at
    todo.updated_at = datetime.now()
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


#add admin users with all permissions
#admin can send bulk notification to all users  