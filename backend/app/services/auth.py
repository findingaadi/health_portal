from datetime import datetime, timedelta
from passlib.hash import pbkdf2_sha256
from jose import jwt, JWTError
from app.config import SECRET_KEY, ALGORITHM

def verify_password(unhashed_pw: str, hashed_pw: str) -> bool:
    return pbkdf2_sha256.verify(unhashed_pw, hashed_pw)

def hash_password(password: str) -> str:
    return pbkdf2_sha256.hash(password)

def create_access_token(data: dict, expiry: timedelta) -> str:
    data_copy = data.copy()
    expire = datetime.utcnow() + expiry
    data_copy.update({"exp": expire})
    return jwt.encode(data_copy, SECRET_KEY, algorithm=ALGORITHM)