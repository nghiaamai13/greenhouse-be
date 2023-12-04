from typing import List
from uuid import UUID

from fastapi import Depends, APIRouter, HTTPException, Security
from sqlalchemy.orm import Session
from starlette import status

from .. import schemas, models, oauth2
from ..database import get_db

router = APIRouter(
    prefix="/api/farm",
    tags=["Farm"]
)


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_farm(farm: schemas.FarmCreate, db: Session = Depends(get_db),
                current_user: models.User = Security(oauth2.get_current_user, scopes=["tenant"])):
    farm_with_name = db.query(models.Farm).filter(models.Farm.name == farm.name).all()
    farm_user_ids = [f.owner_id for f in farm_with_name]
    if current_user.user_id in farm_user_ids:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"A farm with name {farm.name} already exists")
        
    new_farm = models.Farm(owner_id=current_user.user_id, **farm.model_dump())
    db.add(new_farm)
    db.commit()
    db.refresh(new_farm)

    return new_farm


@router.get("/all", response_model=List[schemas.FarmResponse])
def get_all_farm(db: Session = Depends(get_db),
                 current_user: models.User = Depends(oauth2.get_current_user)):
    farms = db.query(models.Farm).filter(models.Farm.owner_id == current_user.user_id).all()

    return farms


@router.get("/{farm_id}", )
def get_farm_by_id(farm_id: UUID, db: Session = Depends(get_db),
                   current_user: models.User = Depends(oauth2.get_current_user)):
    print(current_user)
    farm = db.query(models.Farm).filter(models.Farm.farm_id == farm_id).first()

    if farm.owner_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to access this entity")
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")

    return farm
