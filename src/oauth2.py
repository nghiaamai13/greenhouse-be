from datetime import datetime, timedelta
from uuid import UUID

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from starlette import status
from pydantic import ValidationError

from . import schemas, models, database

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")

SECRET_KEY = "nghia"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_access_token(data: dict):
    to_encode = data.copy()
    expires = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expires})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(security_scopes: SecurityScopes, token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    ) 
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("username")
        user_id: str = payload.get("user_id")
        if username is None:
            raise credentials_exception
        token_scope = payload.get("scope")
        token_data = schemas.TokenData(scope=token_scope, username=username, user_id=user_id)

    except (JWTError, ValidationError) as e:
        print(e)
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.username == username).first()
    
    if len(security_scopes.scopes) != 0 and token_data.scope not in security_scopes.scopes:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not enough permissions",
            headers={"WWW-Authenticate": f"Bearer scope={token_data.scope}"},
        )
    return user

