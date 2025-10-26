from fastapi import FastAPI
from app.database import create_db_and_tables
from app.routers import todos

app=FastAPI(title="Todo API")

@app.on_event("startup")
def on_start_up():
    create_db_and_tables()