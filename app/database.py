from sqlmodel import Session,SQLModel,create_engine

DATABASE_URL = "sqlite:///./todos.db"   # file db (similar to Django default sqlite3)
engine = create_engine(DATABASE_URL, echo=True)  # echo=True prints SQL (helpful during dev)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session