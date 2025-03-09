import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("database_url")

IMMUDDB_HOST = os.getenv("IMMUDDB_HOST")
IMMUDDB_PORT = os.getenv("IMMUDDB_PORT")
IMMUDDB_USER = os.getenv("IMMUDDB_USER")
IMMUDDB_PASSWORD = os.getenv("IMMUDDB_PASSWORD")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
