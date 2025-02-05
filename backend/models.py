from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

#users table

class User(Base):
    __tablename__ = "users" #the tablename in postgresql

    id = Column(Integer, primary_key = True, index = True)
    name = Column(String, nullable= False)
    email = Column(String, unique= True, nullable= False)
    password = Column(String, nullable= False)
    role = Column(String, nullable = False)

    #relationship betweeen the doctor with patient record. 
    #using back_populate in sqlalchemy makes the two relationship bidirectional
    #generic example, i can search for users.doctor and print doctor.records.
    records = relationship("PatientRecord", back_populates="doctor")
    

class PatientRecord(Base):
    __tablename__ = "patient_records"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    record_details = Column(Text, nullable=False)
    timestamp = Column(datetime, default = datetime.utcnow)

    patient = relationship("User", foreign_keys=[patient_id], back_populates="records")
    doctor = relationship("Users", foreign_keys=[doctor_id])