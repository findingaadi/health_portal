from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, Body
from database import engine, SessionLocal
from models import Base,User, PatientRecord
from pydantic import BaseModel, EmailStr
from fastapi import HTTPException
from sqlalchemy.orm import Session
from passlib.hash import pbkdf2_sha256
from typing import List
from jose import jwt, JWTError
import os
from dotenv import load_dotenv
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from immudb.client import ImmudbClient
import time

app = FastAPI()

#create database tables
Base.metadata.create_all(bind=engine)

load_dotenv()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

IMMUDDB_HOST = os.getenv("IMMUDDB_HOST")
IMMUDDB_PORT = os.getenv("IMMUDDB_PORT")
IMMUDDB_USER = os.getenv("IMMUDDB_USER")
IMMUDDB_PASSWORD = os.getenv("IMMUDDB_PASSWORD")

def get_immudb_client(retries=3, delay=2):
    for attempt in range(retries):
        try:
            client = ImmudbClient(f"{IMMUDDB_HOST}:{IMMUDDB_PORT}")
            client.login(IMMUDDB_USER, IMMUDDB_PASSWORD)
            print("immudb logged in")
            return client
        except Exception as e:
            print(f"Attempt {attempt + 1}: immudb login failed. retrying.")
            time.sleep(delay)
    raise RuntimeError("Failed to connect to immudb after multiple attempts")

immu_client = get_immudb_client()



class UserLogin(BaseModel):
    email:EmailStr
    password:str

def verify_password(unhashed_pw: str, hashed_pw:str)->bool:
    return pbkdf2_sha256.verify(unhashed_pw,hashed_pw)
   

@app.post("/login/")
def login(user_credentials: UserLogin, db: Session=Depends(get_db)):
    user = db.query(User).filter(User.email == user_credentials.email).first()
    if not user:
        raise HTTPException(status_code=400, detail= "Invalid email or password")
    
    if not verify_password(user_credentials.password, user.password):
        raise HTTPException(status_code=400, detail= "Invalid email or password")
    
    access_token_expiry = timedelta(minutes=30)
    access_token = create_access_token({"sub": user.email, "role": user.role}, access_token_expiry)


    return{"access_token": access_token, "token_type": "bearer"}

#jwt token to authenticate
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")



def create_access_token(data:dict, expiry):
    data_copy = data.copy()#to prevent the original dictionary to be modified 
    expire = datetime.utcnow()+ expiry
 
    data_copy.update({"exp":expire})
    return jwt.encode(data_copy, SECRET_KEY, ALGORITHM)

#pass the token from authentication header
security = HTTPBearer()
#verify the token
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials #get the token
    try:
        payload = jwt.decode(token, SECRET_KEY, ALGORITHM)
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid authentication")

        user = db.query(User).filter(User.email == email).first()
        if user is None:
            raise HTTPException(status_code=401, detail= "User not found")
    except JWTError:
        raise HTTPException(status_code=401, detail = "Couldn't validate the user credentials")
    return user #returning the authenticated user


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
        from_attributes = True

@app.get("/users/", response_model= List[UserResponse])
# def get_users(db: Session = Depends(get_db), current_user:User = Depends(get_current_user)):
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
        from_attributes = True


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
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: User=Depends(get_current_user)):

    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail= "Access Denied!") 
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code= 400, detail="User not found.")
    
    check_patient_record = db.query(PatientRecord).filter(PatientRecord.patient_id == user.id).first()
    if check_patient_record:
        raise HTTPException(status_code=403, detail = "Cannot delete the patient as there is records for this patient")
    
    check_doctor_id = db.query(PatientRecord).filter(PatientRecord.doctor_id == user.id).first()
    if check_doctor_id:
        raise HTTPException(status_code=403, detail="Cannot delete the doctor as there is records made by the doctor")
    
    db.delete(user)
    db.commit()
    return{f"User {user.name} has been deleted from the records."}

class PatientRecordCreate(BaseModel):
    patient_id: int
    record_details: str

class PatientRecordResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    record_details: str
    timestamp: datetime

    class Config:
        from_attributes = True

@app.post("/records/", response_model=PatientRecordResponse)
def create_patient_records(record: PatientRecordCreate, db : Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    patient = db.query(User).filter(User.id == record.patient_id, User.role == "patient").first()
    if not patient:
        raise HTTPException(status_code=404, detail= "User not found")

    if current_user.role != "doctor":
        raise HTTPException(status_code=403, detail= "Only doctors can add a patients record.")
        
    new_record = PatientRecord(
        patient_id = record.patient_id,
        doctor_id = current_user.id,
        record_details = record.record_details,
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)

    log_access(patient.id, current_user.id, "Created")
    return new_record

#to log into immudb
def log_access(patient_id: int, doctor_id: int, action: str):
    try:
        log_entry = f"Doctor {doctor_id} {action} medical record of Patient {patient_id} at {datetime.now()}."
        immu_client.set(str(patient_id).encode("utf-8"), log_entry.encode("utf-8"))
    except Exception as e:
        print(f"failed to log access in immudb: {e}")


@app.get("/records/", response_model=List[PatientRecordResponse])
def get_all_records(db: Session = Depends(get_db), current_user : User= Depends(get_current_user)):

    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail= "Access denied!")
    
    records = db.query(PatientRecord).all()
    if not records:
        raise HTTPException(status_code=404, detail= "No Patient record found.")
    return records


@app.get("/records/patient/{patient_id}", response_model= List[PatientRecordResponse])
def get_records_by_patient(patient_id: int, db: Session=Depends(get_db), current_user: User = Depends(get_current_user)):

    verify_patient = db.query(User).filter(User.id == patient_id, User.role == "patient").first()
    if not verify_patient:
            raise HTTPException(status_code=403, detail = "Patient not found.")
    
    patient_records = db.query(PatientRecord).filter(PatientRecord.patient_id == patient_id).all()
    if not patient_records:
        raise HTTPException(status_code=403, detail= "Record not found.")
    
    if current_user.id != patient_id and current_user.role != "doctor":
        raise HTTPException(status_code=403, detail = "You can only view your own records.")
    
    log_access(patient_id, current_user.id, "Viewed")


    return patient_records


@app.get("/records/doctor/{doctor_id}", response_model= List[PatientRecordResponse])
def get_records_by_doctor(doctor_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):

    if current_user.id != doctor_id:
        raise HTTPException(status_code=403, detail= "You can only view the records of your own patients.")

    doctor_records = db.query(PatientRecord).filter(PatientRecord.doctor_id == doctor_id).first()
    if not doctor_records:
        raise HTTPException(status_code=404, detail= "Record not found.")
    return doctor_records

class PatientRecordUpdate(BaseModel):
    record_details:str | None = None

    class Config:
        from_attributes= True

@app.put("/records/update/{record_id}", response_model = PatientRecordResponse)
def update_record(record_id: int, record_update: PatientRecordUpdate= Body(...),db: Session=Depends(get_db), current_user : User = Depends(get_current_user)):
    record = db.query(PatientRecord).filter(PatientRecord.id == record_id).first()
    if not record: 
        raise HTTPException(status_code=404, detail="Record not found.")
    
    if current_user.id != record.doctor_id:
        raise HTTPException(status_code=403, detail="Only doctor who made the record can edit the record.")
    
    if record_update.record_details:
        record.record_details = record_update.record_details

        db.commit()
        db.refresh(record)
        log_access(record.patient_id, current_user.id, "Updated")
        return record

@app.delete("/records/delete/{record_id}")
def delete_record(record_id: int, db:Session=Depends(get_db), current_user: User= Depends(get_current_user)):
    record = db.query(PatientRecord).filter(record_id == PatientRecord.id).first()
    if not record:
        raise HTTPException(status_code=404, detail= "Record not found")
    if current_user.id != record.doctor_id:
        raise HTTPException(status_code=403, detail= "Only the doctor who created the record is allowed to delete it.")
    
    log_access(record.patient_id, current_user.id, "Deleted")
    
    db.delete(record)
    db.commit()
    return{"message":f"The Patient {record.patient_id} has had their record: {record.id} deleted."}


@app.get("/immdb/log/{patient_id}")
def get_immdb_logs(patient_id: int):
    try:
        key = str(patient_id).encode("utf-8")
        log_entry = immu_client.history(key,0,100,True)
        logs =[]

        if not log_entry:
            return {"message": "No logs found for this patient."}
        
        for entry in log_entry:
            entry_log = entry.value.decode("utf-8")
            logs.append({"Patient": patient_id,"log": entry_log})
        return logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Immudb error: {e}")

# @app.get("/immdb/all-keys")
# def get_all_keys():
#     try:
#         keys = immu_client.scan("", 100, False)
#         return [entry.key.decode("utf-8") for entry in keys.entries]
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error fetching keys: {str(e)}")
