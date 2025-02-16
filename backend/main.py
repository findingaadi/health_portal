from datetime import datetime
from fastapi import FastAPI, Depends, Body
from database import engine, SessionLocal
from models import Base,User, PatientRecord
from pydantic import BaseModel, EmailStr
from fastapi import HTTPException
from sqlalchemy.orm import Session
from passlib.hash import pbkdf2_sha256
from typing import List

app = FastAPI()

#create database tables
Base.metadata.create_all(bind=engine)


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
        raise HTTPException(status_code=400, detail ="email already taken by another user")
    
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
    class Config: 
        orm_model = True

@app.get("/users/", response_model= List[UserResponse])
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users


# To view a specific user based on their userID
@app.get("/users/{user_id}", response_model= UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail= "User not found.")
    return user


# To update a users details

class UserUpdate(BaseModel):
    name: str | None = None # this leaves the ones that are not updated as it is
    email: EmailStr | None = None 
    role : str | None = None
    
    class Config: 
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
        raise HTTPException(status_code= 404, detail= "User not found.")
    
    if user_update.name:
        user.name = user_update.name

    if user_update.email:
        # check if the provided email is already existing or not
        existing_user = db.query(User).filter(User.email == user_update.email, User.id != user_id).first()
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
        raise HTTPException(status_code= 400, detail="User not found.")
    
    db.delete(user)
    db.commit()
    return{f"User {user.name} has been deleted from the records."}

class PatientRecordCreate(BaseModel):
    patient_id: int
    doctor_id: int
    record_details: str

class PatientRecordResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    record_details: str
    timestamp: datetime

    class Config:
        orm_mode = True

@app.post("/records/", response_model=PatientRecordResponse)
def create_patient_records(record: PatientRecordCreate, db : Session = Depends(get_db)):
    patient = db.query(User).filter(User.id == record.patient_id, User.role == "patient").first()
    if not patient:
        raise HTTPException(status_code=404, detail= "User not found")

    doctor = db.query(User).filter(User.id == record.doctor_id, User.role == "doctor").first()
    if not doctor:
        raise HTTPException(status_code=404, detail= "User not found")
        
    new_record = PatientRecord(
        patient_id = record.patient_id,
        doctor_id = record.doctor_id,
        record_details = record.record_details,
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    return new_record

@app.get("/records/", response_model=List[PatientRecordResponse])
def get_all_records(db: Session = Depends(get_db)):
    records = db.query(PatientRecord).all()
    if not records:
        raise HTTPException(status_code=404, detail= "No Patient record found.")
    return records


@app.get("/records/patient/{patient_id}", response_model= List[PatientRecordResponse])
def get_records_by_patient(patient_id: int, db: Session=Depends(get_db)):

    verify_patient = db.query(User).filter(User.id == patient_id, User.role == "patient").first()
    if not verify_patient:
            raise HTTPException(status_code=404, detail = "Patient not found.")
    
    patient_records = db.query(PatientRecord).filter(PatientRecord.patient_id == patient_id).all()
    if not patient_records:
        raise HTTPException(status_code=404, detail= "Record not found.")
    return patient_records


@app.get("/records/doctor/{doctor_id}", response_model= List[PatientRecordResponse])
def get_records_by_doctor(doctor_id: int, db: Session = Depends(get_db)):
    doctor_records = db.query(PatientRecord).filter(PatientRecord.doctor_id == doctor_id).first()
    if not doctor_records:
        raise HTTPException(status_code=404, detail= "Record not found.")
    return doctor_records

class PatientRecordUpdate(BaseModel):
    record_details:str | None = None

    class Config:
        orm_model= True

@app.put("/records/update/{record_id}", response_model = PatientRecordResponse)
def update_record(record_id: int, doctor_id:int, record_update: PatientRecordUpdate= Body(...),db: Session=Depends(get_db)):
    record = db.query(PatientRecord).filter(PatientRecord.id == record_id).first()
    if not record: 
        raise HTTPException(status_code=404, detail="Record not found.")
    # verify_doctor = db.query(User).filter(User.id == record.doctor_id, User.role == "doctor").first()
    if (doctor_id != record.doctor_id):
        raise HTTPException(status_code=403, detail="Only doctor who made the record can edit the record.")
    
    if record_update.record_details:
        record.record_details = record_update.record_details

        db.commit()
        db.refresh(record)
        return record

@app.delete("/records/delete/{record_id}")
def delete_record(record_id: int,doctor_id:int, db:Session=Depends(get_db)):
    record = db.query(PatientRecord).filter(record_id == PatientRecord.id).first()
    if not record:
        raise HTTPException(status_code=404, detail= "Record not found")
    if (doctor_id != record.doctor_id):
        raise HTTPException(status_code=403, detail= "Only the doctor who created the record is allowed to delete it.")
    
    db.delete(record)
    db.commit()
    return{"message":f"The Patient{record.patient_id} has had their record: {record.id} deleted."}

#authentication

class UserLogin(BaseModel):
    email:EmailStr
    password:str

def verify_password(unhashed_pw: str, hashed_pw:str)->bool:
    return pbkdf2_sha256.verify(unhashed_pw,hashed_pw) #this was pain to get to initially, should've looked at documentation earlier. 
   

@app.post("/login/")
def login(user_credentials: UserLogin, db: Session=Depends(get_db)):
    user = db.query(User).filter(user_credentials.email == User.email).first()
    if not user:
        raise HTTPException(status_code=404, detail= "user Email not found") #this is for now to test where the execption is raised
    
    if not verify_password(user_credentials.password, user.password):
        raise HTTPException(status_code=404, detail= "Invalid email or password")
    
    return{"message": "Login Successful"}
