from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import List
from app.database import SessionLocal
from app.models import User
from app.services.auth import verify_password, hash_password, create_access_token
from datetime import timedelta
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from app.config import SECRET_KEY, ALGORITHM

router = APIRouter()
security = HTTPBearer()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid authentication")
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
    except JWTError:
        raise HTTPException(status_code=401, detail="Couldn't validate the user credentials")
    return user

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    role: str | None = None

    class Config:
        from_attributes = True

@router.post("/login/")
def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_credentials.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid email or password")
    if not verify_password(user_credentials.password, user.password):
        raise HTTPException(status_code=400, detail="Invalid email or password")
    access_token_expiry = timedelta(minutes=30)
    # Passing the user id as string as int isnt accepted
    access_token = create_access_token({"sub": str(user.id), "role": user.role, "name": user.name}, access_token_expiry)
    return {"access_token": access_token, "token_type": "bearer", "role":user.role}

@router.post("/users/", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="email already taken by another user")
    hashed_password = hash_password(user.password)
    new_user = User(
        name=user.name,
        email=user.email,
        password=hashed_password,
        role=user.role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.get("/users/", response_model=List[UserResponse])
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users

@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied!")
    return current_user

@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user_update: UserUpdate = Body(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if user_update.name:
        user.name = user_update.name
    if user_update.email:
        existing_user = db.query(User).filter(User.email == user_update.email, User.id != user_id).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="email is already in use.")
        user.email = user_update.email
    if user_update.role:
        user.role = user_update.role
    db.commit()
    db.refresh(user)
    return user

@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.models import PatientRecord  # Import here to avoid circular imports
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access Denied!")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found.")
    check_patient_record = db.query(PatientRecord).filter(PatientRecord.patient_id == user.id).first()
    if check_patient_record:
        raise HTTPException(status_code=403, detail="Cannot delete the patient as there is records for this patient")
    check_doctor_id = db.query(PatientRecord).filter(PatientRecord.doctor_id == user.id).first()
    if check_doctor_id:
        raise HTTPException(status_code=403, detail="Cannot delete the doctor as there is records made by the doctor")
    db.delete(user)
    db.commit()
    return {f"User {user.name} has been deleted from the records."}