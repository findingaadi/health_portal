from fastapi import FastAPI, Depends
from database import engine, SessionLocal
from models import Base,User, PatientRecord
from pydantic import BaseModel
from fastapi import HTTPException
from sqlalchemy.orm import Session

app = FastAPI()

#create database tables
Base.metadata.create_all(bind=engine)

@app.get("/")
def home():
    return {"message":"welcome!"}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


#schema to create a new user
class UserCreate(BaseModel):
    name:str
    email:str
    password:str
    role:str


@app.post("/users/")
def create_user(user: UserCreate,db: Session =Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, details ="email already taken by another user")
    
    new_user = User(
        name = user.name,
        email = user.email,
        password = user.password,
        role = user.role 
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

