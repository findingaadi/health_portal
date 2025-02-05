from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

# Users Table
class User(Base):
    __tablename__ = "users"  # The table name in PostgreSQL

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # doctor or patient

    # Relationships
    # This establishes a bidirectional relationship between User and PatientRecord for doctors
    doctor_records = relationship("PatientRecord", back_populates="doctor", foreign_keys="PatientRecord.doctor_id")

    # This establishes a bidirectional relationship between User and PatientRecord for patients
    patient_records = relationship("PatientRecord", back_populates="patient", foreign_keys="PatientRecord.patient_id")


# Patient Records Table
class PatientRecord(Base):
    __tablename__ = "patient_records"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False) 
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)  
    record_details = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    patient = relationship("User", back_populates="patient_records", foreign_keys=[patient_id])
    doctor = relationship("User", back_populates="doctor_records", foreign_keys=[doctor_id])