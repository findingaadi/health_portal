from fastapi import FastAPI, Depends
from database import engine, SessionLocal
from models import Base,User, PatientRecord
from pydantic import BaseModel, EmailStr
from fastapi import HTTPException
from sqlalchemy.orm import Session
from passlib.hash import pbkdf2_sha256
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
    email:EmailStr
    password:str
    role:str


def hash_password(password:str):
    return pbkdf2_sha256.hash(password)

@app.post("/users/")
def create_user(user: UserCreate,db: Session =Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, details ="email already taken by another user")
    
    hashed_password = hash_password(user.password)

    new_user = User(
        name = user.name,
        email = user.email,
        password = hashed_password,
        role = user.role 
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

