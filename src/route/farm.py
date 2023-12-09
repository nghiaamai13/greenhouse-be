from typing import List
from uuid import UUID
import json
import datetime

from fastapi import Depends, APIRouter, HTTPException, Security, Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from starlette import status

from .. import schemas, models, oauth2
from ..database import get_db

router = APIRouter(
    prefix="/api/farm",
    tags=["Farm"]
)


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_farm(farm: schemas.FarmCreate, db: Session = Depends(get_db),
                current_user: models.User = Security(oauth2.get_current_user,
                                                     scopes=["tenant"])):
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
                 current_user: models.User = Security(oauth2.get_current_user,
                                                      scopes=["tenant", "customer"])):
    if current_user.role == "tenant":
        farms = db.query(models.Farm).filter(models.Farm.owner_id == current_user.user_id).all()
    elif current_user.role == "customer":
        farms = db.query(models.Farm).filter(models.Farm.assigned_customer == current_user.user_id).all()
    return farms


@router.get("/{farm_id}", response_model=schemas.FarmResponse)
def get_farm_by_id(farm_id: UUID, db: Session = Depends(get_db),
                   current_user: models.User = Security(oauth2.get_current_user,
                                                        scopes=["tenant", "customer"])):
    farm = db.query(models.Farm).filter(models.Farm.farm_id == farm_id).first()
    
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Farm not found")
        
    if not ((current_user.role == "customer" and (current_user.user_id==farm.assigned_customer))
        or (current_user.role == "tenant" and farm.owner_id == current_user.user_id)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="You have no access to this farm")
        
    return farm
    
   
@router.delete("/{farm_id}", status_code=status.HTTP_200_OK)
def delete_farm(farm_id: UUID, db: Session = Depends(get_db),
                current_user: models.User = Security(oauth2.get_current_user, scopes=["tenant"])):
    farm = db.query(models.Farm).filter(models.Farm.farm_id == farm_id)
    if farm.first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Farm not found")
    if farm.first().owner_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="You must be the owner of this entity to delete")
    
    farm.delete(synchronize_session=False)
    db.commit()
    
    return Response(status_code=200, content="Successfully deleted farm")


@router.post("/{farm_id}/customer/{customer_id}")
def assign_farm_to_customer(farm_id: UUID, customer_id: UUID, db: Session = Depends(get_db),
                            current_user: models.User = Security(oauth2.get_current_user,
                                                                 scopes=["tenant"])):
    farm_query = db.query(models.Farm).filter(models.Farm.farm_id == farm_id, 
                                              models.Farm.owner_id == current_user.user_id)
    farm = farm_query.first()
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")
    
    customer = db.query(models.User).filter(models.User.user_id == customer_id,
                                            models.User.created_by == current_user.user_id).first()
    if not customer or customer.role != "customer":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Customer not found")

    if farm.assigned_customer is None:
        farm.assigned_customer = customer.user_id
        db.commit()
        return Response(status_code=status.HTTP_200_OK, 
                        content=json.dumps({"detail": "Successfully assigned farm to customer"}),
                        media_type="application/json")
    
    if farm.assigned_customer is not None and farm.assigned_customer != customer.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Farm assigned to other customer")
    else:
        farm.assigned_customer = None
        db.commit()
        return Response(status_code=status.HTTP_200_OK,
                        content=json.dumps({"detail": "Successfully unassigned farm from customer"}),
                        media_type="application/json")


@router.get("/{farm_id}/keys/all", response_model=List[schemas.TSKeyBase])
def get_all_farm_keys(farm_id: UUID, db: Session = Depends(get_db),
                      current_user: models.User = Security(oauth2.get_current_user,
                                                          scopes=["tenant", "customer"])):
    if current_user.role == 'tenant':
        farm = db.query(models.Farm).filter(models.Farm.farm_id == farm_id, 
                                            models.Farm.owner_id == current_user.user_id).first()
    else:
        farm = db.query(models.Farm).filter(models.Farm.farm_id == farm_id, 
                                            models.Farm.assigned_customer == current_user.user_id).first()
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Farm not found")
    return farm.farm_keys
    
    
@router.get("/{farm_id}/threshold/all")
def get_thresholds_of_farm(farm_id: UUID, db: Session = Depends(get_db),
                           current_user: models.User = Security(oauth2.get_current_user,
                                                                  scopes=["tenant", "customer"])):
    farm: models.Farm = get_farm_by_id(farm_id, db, current_user)
    
    thresholds = db.query(models.Threshold).filter(models.Threshold.farm_id==farm_id).all()

    return thresholds
    
    
@router.post("/{farm_id}/threshold/{key}")
def set_farm_threshold_on_key(farm_id: UUID, key: str,
                              max_value: float,
                              min_value: float,
                              db: Session = Depends(get_db),
                              current_user: models.User = Security(oauth2.get_current_user,
                                                              scopes=["tenant", "customer"])):
    farm: models.Farm = get_farm_by_id(farm_id, db, current_user)
    valid_keys = [key.ts_key for key in farm.farm_keys]
    
    if key not in valid_keys:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Invalid farm key")
    
    if min_value >= max_value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Max value must be larger than min value")
     
    existing_threshold = db.query(models.Threshold).filter(models.Threshold.farm_id==farm_id,
                                                              models.Threshold.key==key).first()
    if existing_threshold:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Threshold for the specified farm and key already exists, use update threshold instead.")
    
        
    new_threshold = models.Threshold(farm_id=farm_id, key=key,
                                     threshold_max=max_value, threshold_min=min_value,
                                     modified_by=current_user.user_id)
    
    db.add(new_threshold)
    db.commit()
    db.refresh(new_threshold)

    return new_threshold


@router.put("/{farm_id}/threshold/{key}")
def update_farm_threshold_on_key(farm_id: UUID, key: str,
                                 new_max_value: float = None,
                                 new_min_value: float = None,
                                 db: Session = Depends(get_db),
                                 current_user: models.User = Security(oauth2.get_current_user,
                                                                  scopes=["tenant", "customer"])):
    
    existing_threshold = db.query(models.Threshold).filter(models.Threshold.farm_id==farm_id,
                                                           models.Threshold.key==key).first()
    
    if not existing_threshold:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Threshold not found for the specified farm and key")
        
    if new_max_value is None and new_min_value is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Please provide at least one threshold value")
        
    elif new_min_value is not None and new_max_value is not None and new_min_value >= new_max_value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Max value must be larger than min value")
        
    elif (new_min_value is not None 
          and new_max_value is None 
          and existing_threshold.threshold_max is not None 
          and new_min_value >= existing_threshold.threshold_max):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="New min value cannot be larger than the existing max value")
        
    elif (new_max_value is not None 
          and new_min_value is None 
          and existing_threshold.threshold_min is not None 
          and new_max_value <= existing_threshold.threshold_min):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="New max value cannot be larger than the existing min value")
    
    existing_threshold.threshold_max = new_max_value if new_max_value is not None else existing_threshold.threshold_max
    existing_threshold.threshold_min = new_min_value if new_min_value is not None else existing_threshold.threshold_min
    existing_threshold.modified_by = current_user.user_id
    existing_threshold.modified_at = datetime.datetime.now()
    
    db.commit()
    db.refresh(existing_threshold)

    return existing_threshold


@router.delete("/{farm_id}/threshold/{key}")
def delete_farm_threshold_with_key(farm_id: UUID, key: str,
                                   db: Session = Depends(get_db),
                                   current_user: models.User = Security(oauth2.get_current_user,
                                                                 scopes=["tenant", "customer"])):
    
    farm: models.Farm = get_farm_by_id(farm_id, db, current_user)
    existing_threshold = db.query(models.Threshold).filter(models.Threshold.farm_id==farm_id,
                                                           models.Threshold.key==key)
    if not existing_threshold.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail={"Threshold not found for the specified farm and key"})
    
    existing_threshold.delete(synchronize_session=False)
    
    db.commit()

    return Response(status_code=200, content="Successfully deleted threshold")