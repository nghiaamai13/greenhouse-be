from fastapi import Depends, APIRouter, HTTPException, Security
from fastapi.security import SecurityScopes
from sqlalchemy.orm import Session
from starlette import status

from src import schemas, models, utils, oauth2
from ..database import get_db


router = APIRouter(
    prefix="/api",
    tags=["User"]
)


@router.post("/customer", status_code=status.HTTP_201_CREATED, response_model=schemas.UserResponse)
def create_customer(user_credentials: schemas.UserCreate, db: Session = Depends(get_db),
                    current_user: models.User = Security(oauth2.get_current_user, scopes=["tenant"])):
    
    username = db.query(models.User).filter(models.User.username == user_credentials.username).first()
    if username:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    hashed_password = utils.get_password_hash(user_credentials.password)
    user_credentials.password = hashed_password
    new_user = models.User(created_by=current_user.user_id, **user_credentials.model_dump())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/tenant", status_code=status.HTTP_201_CREATED, response_model=schemas.UserResponse)
def create_tenant(user_credentials: schemas.TenantCreate, db: Session = Depends(get_db),
                    current_user: models.User = Security(oauth2.get_current_user, scopes=["admin"])):
    
    username = db.query(models.User).filter(models.User.username == user_credentials.username).first()
    if username:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    hashed_password = utils.get_password_hash(user_credentials.password)
    user_credentials.password = hashed_password
    new_user = models.User(created_by=current_user.user_id, **user_credentials.model_dump())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user



