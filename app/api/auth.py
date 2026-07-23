import os
from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 hours

import bcrypt
import hashlib

def verify_password(plain_password, hashed_password):
    # Passlib has a known bug with bcrypt > 4.0, so we use bcrypt directly.
    sha256_hash = hashlib.sha256(plain_password.encode('utf-8')).hexdigest().encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(sha256_hash, hashed_bytes)

def get_password_hash(password):
    # Passlib has a known bug with bcrypt > 4.0, so we use bcrypt directly.
    sha256_hash = hashlib.sha256(password.encode('utf-8')).hexdigest().encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(sha256_hash, salt)
    return hashed.decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = 15

def create_password_reset_token(user_id: str) -> str:
    expires_delta = timedelta(minutes=PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": str(user_id),
        "type": "password_reset",
        "exp": datetime.utcnow() + expires_delta
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_password_reset_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "password_reset":
            return None
        user_id: str = payload.get("sub")
        return user_id
    except JWTError:
        return None

