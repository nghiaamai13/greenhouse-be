from fastapi import Depends, APIRouter, HTTPException
from sqlalchemy.orm import Session
from starlette import status

from src import schemas, models, utils
from src.database import get_db


router = APIRouter(
    prefix="/user",
    tags=["User"]
)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.UserResponse)
def create_user(user_credentials: schemas.UserCreate, db: Session = Depends(get_db)):

    username = db.query(models.User).filter(models.User.username == user_credentials.username).first()
    if username:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")

    hashed_password = utils.get_password_hash(user_credentials.password)
    user_credentials.password = hashed_password

    new_user = models.User(**user_credentials.model_dump())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.get('/{user_id}', response_model=schemas.UserResponse)
def get_user_by_id(user_id: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.user_id == user_id).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user
