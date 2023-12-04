from typing import List
from uuid import UUID

from fastapi import Depends, APIRouter, HTTPException, Security, Response
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
                 current_user: models.User = Security(oauth2.get_current_user, scopes=["tenant", "customer"])):
    if current_user.role == "tenant":
        farms = db.query(models.Farm).filter(models.Farm.owner_id == current_user.user_id).all()
    elif current_user.role == "customer":
        farms = db.query(models.Farm).filter(models.Farm.assigned_customers.any(user_id=current_user.user_id)).all()
    return farms


@router.get("/{farm_id}", response_model=schemas.FarmResponse)
def get_farm_by_id(farm_id: UUID, db: Session = Depends(get_db),
                   current_user: models.User = Security(oauth2.get_current_user, scopes=["tenant", "customer"])):
    farm = db.query(models.Farm).filter(models.Farm.farm_id == farm_id).first()
    if not ((current_user.role == "customer" and (current_user.user_id in farm.assigned_customers))
        or (current_user.role == "tenant" and farm.owner_id == current_user.user_id)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found or no access")
    return farm
    
   
@router.delete("/{farm_id}", status_code=status.HTTP_200_OK)
def delete_farm(farm_id: UUID, db: Session = Depends(get_db),
                current_user: models.User = Security(oauth2.get_current_user, scopes=["tenant"])):
    farm = db.query(models.Farm).filter(models.Farm.farm_id == farm_id)
    if farm.first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")
    if farm.first().owner_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You must be the owner of this entity to delete")
    
    farm.delete(synchronize_session=False)
    db.commit()
    
    return Response(status_code=200, content="Successfully deleted farm")


@router.post("/{farm_id}/customer/{customer_id}", response_model=schemas.FarmResponse)
def assign_customer_to_farm(farm_id: UUID, customer_id: UUID, db: Session = Depends(get_db),
                            current_user: models.User = Security(oauth2.get_current_user, scopes=["tenant"])):
    farm_query = db.query(models.Farm).filter(models.Farm.farm_id == farm_id, 
                                              models.Farm.owner_id == current_user.user_id)
    farm = farm_query.first()
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")
    
    customer = db.query(models.User).filter(models.User.user_id == customer_id,
                                            models.User.created_by == current_user.user_id).first()
    if not customer or customer.role != "customer":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    if customer in farm.assigned_customers:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Customer is already assigned to the farm")

    farm.assigned_customers.append(customer)
    db.commit()
    return farm