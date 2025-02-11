from fastapi import FastAPI, Depends, Body
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

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str

    # To receive the response as in JSON format
    class config: 
        orm_model = True

@app.get("/users/", response_model= list[UserResponse])
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users


# To view a specific user based on their userID
@app.get("/users/{user_id}", response_model= UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail= "user is not found, please try again.")
    return user


# To update a users details

class UserUpdate(BaseModel):
    name: str | None = None # this leaves the ones that are not updated as it is
    email: EmailStr | None = None 
    role : str | None = None
    
    class config: 
        orm_model = True


"""
there was an error with the post endpoint to update a user,
the fastapi was misinterpreting the user_update as a query parameter,
added the body(...) forcing the fastapi to read the request as a body of JSON, 
can declare the userid and then update its attributes on uvicorn. 
"""

@app.put("/users/{user_id}", response_model = UserResponse)
def update_user(user_id: int, user_update: UserUpdate = Body(...) , db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code= 404, detail= "user not found, please try again.")
    
    if user_update.name:
        user.name = user_update.name

    if user_update.email:
        # check if the provided email is already existing or not
        existing_user = db.query(User).filter(User.email == user_update.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="email is already in use.")
        # if not then update the email
        user.email = user_update.email

    if user_update.role:
        user.role = user_update.role
    
    db.commit()
    db.refresh(user)
    return user


@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code= 400, detail="user not found, please try again.")
    
    db.delete(user)
    db.commit()
    return{user.name,"has been deleted off the record."}