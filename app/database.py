from sqlmodel import Session,SQLModel,create_engine

# Create SQLite database engine (like Django settings.DATABASES)
DATABASE_URL = "sqlite:///./todos.db"   # file db (similar to Django default sqlite3)
engine = create_engine(DATABASE_URL, echo=True)  # echo=True prints SQL (helpful during dev)

# This function creates tables for all models
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# Dependency that will be used in FastAPI routes
# It opens a session and closes it automatically when done.
def get_session():
    with Session(engine) as session:
        yield session