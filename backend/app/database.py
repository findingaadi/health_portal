from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
from app.config import DATABASE_URL


load_dotenv()
#postgres connection url using docker hostname, passoword and database name from docker-compose.yml
DATABASE_URL = os.getenv("database_url")

#the engine handles communication between fastapi and the database. 
#create the engine
engine = create_engine(DATABASE_URL)

#the sessionlocal allows to query the database with commands like select and insert
SessionLocal = sessionmaker(autocommit = False, autoflush = False, bind = engine)

#base class for all models, its used to define tables/models in the database. 
Base = declarative_base()

