from fastapi import FastAPI,Depends
from contextlib import asynccontextmanager
from db import engine,get_session
from sqlmodel import SQLModel,Session,select
from models import User

@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield



app = FastAPI(lifespan=lifespan)

@app.get("/health")
def health_check():
    return {"status":"ok","service":"user-service"}

@app.post("/users/")
def create_user(user: User, session: Session=Depends(get_session)):
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@app.get("/users/")
def read_users(session:Session =Depends(get_session)):
    users= session.exec(select(User)).all()
    return users