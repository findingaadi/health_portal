from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from datetime import datetime
from app.database import SessionLocal
from app.models import PatientRecord, User
from app.services.auth import create_access_token
from .immudb_client import log_access
from .immudb_client import immu_client
from jose import jwt, JWTError
from app.config import SECRET_KEY, ALGORITHM
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

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
        user_id = int(payload.get("sub"))  

        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication")
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
    except JWTError as e:
        print("error JWT:", str(e))
        raise HTTPException(status_code=401, detail="Couldn't validate the user credentials")
    return user

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

class PatientRecordUpdate(BaseModel):
    record_details: str | None = None

    class Config:
        from_attributes = True

@router.post("/records/", response_model=PatientRecordResponse)
def create_patient_records(record: PatientRecordCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    patient = db.query(User).filter(User.id == record.patient_id, User.role == "patient").first()
    if not patient:
        raise HTTPException(status_code=404, detail="User not found")
    if current_user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can add a patient's record.")
    new_record = PatientRecord(
        patient_id=record.patient_id,
        doctor_id=current_user.id,
        record_details=record.record_details,
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    # log_access(patient.id, current_user.id, "Created")
    return new_record

@router.get("/records/", response_model=List[PatientRecordResponse])
def get_all_records(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied!")
    records = db.query(PatientRecord).all()
    if not records:
        raise HTTPException(status_code=404, detail="No Patient record found.")
    return records

@router.get("/records/patient/{patient_id}", response_model=List[PatientRecordResponse])
def get_records_by_patient(patient_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    verify_patient = db.query(User).filter(User.id == patient_id, User.role == "patient").first()
    if not verify_patient:
        raise HTTPException(status_code=403, detail="Patient not found.")
    patient_records = db.query(PatientRecord).filter(PatientRecord.patient_id == patient_id).all()
    if not patient_records:
        raise HTTPException(status_code=403, detail="Record not found.")
    if current_user.id != patient_id and current_user.role != "doctor":
        raise HTTPException(status_code=403, detail="You can only view your own records.")
    # if current_user.id != patient_id:
        # log_access(patient_id, current_user.id, "Viewed")
    
    return patient_records

@router.get("/records/doctor/{doctor_id}", response_model=List[PatientRecordResponse])
def get_records_by_doctor(doctor_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.id != doctor_id:
        raise HTTPException(status_code=403, detail="You can only view the records of your own patients.")
    doctor_records = db.query(PatientRecord).filter(PatientRecord.doctor_id == doctor_id).all()
    if not doctor_records:
        raise HTTPException(status_code=404, detail="Record not found.")
    return doctor_records

@router.put("/records/update/{record_id}", response_model=PatientRecordResponse)
def update_record(record_id: int, record_update: PatientRecordUpdate = Body(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    record = db.query(PatientRecord).filter(PatientRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found.")
    if current_user.id != record.doctor_id:
        raise HTTPException(status_code=403, detail="Only doctor who made the record can edit the record.")
    if record_update.record_details:
        record.record_details = record_update.record_details
        db.commit()
        db.refresh(record)
        # log_access(record.patient_id, current_user.id, "Updated")
        return record

@router.delete("/records/delete/{record_id}")
def delete_record(record_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    record = db.query(PatientRecord).filter(PatientRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    if current_user.id != record.doctor_id:
        raise HTTPException(status_code=403, detail="Only the doctor who created the record is allowed to delete it.")
    # log_access(record.patient_id, current_user.id, "Deleted")
    db.delete(record)
    db.commit()
    return {"message": f"The Patient {record.patient_id} has had their record: {record.id} deleted."}

@router.get("/immdb/log/{patient_id}")
def get_immdb_logs(patient_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.id != patient_id:
        raise HTTPException(status_code = 403, detail= "You can only view your own logs")
    try:
        key = str(patient_id).encode("utf-8")
        log_entry = immu_client.history(key, 0, 100, True)
        logs = []
        if not log_entry:
            return {"message": "No logs found for this patient."}
        for entry in log_entry:
            entry_log = entry.value.decode("utf-8")
            logs.append({"Patient": patient_id, "log": entry_log})
        return logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Immudb error: {e}")