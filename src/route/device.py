import json
from typing import List
from uuid import UUID

from fastapi import Depends, APIRouter, HTTPException, Security, Response
from sqlalchemy.orm import Session
from starlette import status

from .. import schemas, models, oauth2, mqtt
from ..database import get_db

router = APIRouter(
    prefix="/api/device",
    tags=["Device"]
)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.DeviceResponse)
def create_device(device: schemas.DeviceCreate, db: Session = Depends(get_db),
                  current_user: models.User = Security(oauth2.get_current_user, scopes=["tenant"])):
    
    farm_query = db.query(models.Farm).filter(models.Farm.farm_id == device.farm_id, 
                                              models.Farm.owner_id == current_user.user_id)
    farm = farm_query.first()
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")

    profile_query = db.query(models.DeviceProfile).filter(models.DeviceProfile.profile_id == device.device_profile_id,
                                                          models.DeviceProfile.owner_id == current_user.user_id)
    profile = profile_query.first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    same_device_name = db.query(models.Device).filter(models.Device.name == device.name).all()
    farm_ids = [dev.farm_id for dev in same_device_name]
    if device.farm_id in farm_ids:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"The device with name {device.name} already exists in this farm")     
    
    new_device = models.Device(**device.model_dump())
    db.add(new_device)
    db.commit()
    db.refresh(new_device)
    mqtt.mqtt_subscriber.subscribe_all()
    return new_device


@router.get('/all', response_model=List[schemas.DeviceResponse])
def get_all_devices(db: Session = Depends(get_db),
                    current_user: models.User = Security(oauth2.get_current_user,
                                                         scopes=["tenant", "customer"])):
    if current_user.role == "tenant":
        devices = (db.query(models.Device)
                            .join(models.Farm, models.Device.farm_id == models.Farm.farm_id, isouter=True)
                            .filter(models.Farm.owner_id == current_user.user_id).all())
    else:
        devices = (db.query(models.Device)
                            .join(models.Farm, models.Device.farm_id == models.Farm.farm_id, isouter=True)
                            .filter(models.Farm.assigned_customer == current_user.user_id).all())
        
    return devices


@router.get("/{device_id}", response_model=schemas.DeviceResponse)
def get_device_by_id(device_id: UUID, db: Session = Depends(get_db),
                     current_user: models.User = Depends(oauth2.get_current_user)):
    try:
        device, tenant_id, customer_id = (db.query(models.Device, models.Farm.owner_id, models.Farm.assigned_customer)
                         .join(models.Farm, models.Device.farm_id == models.Farm.farm_id, isouter=True)
                         .filter(models.Device.device_id == device_id).first())
    except TypeError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    print(device,  tenant_id, customer_id)
    
    if tenant_id == current_user.user_id or customer_id == current_user.user_id:
        return device
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="You do not have permission to access this entity")

    


@router.post("/profile", status_code=status.HTTP_201_CREATED,
             response_model=schemas.DeviceProfileResponse)
def create_device_profile(profile: schemas.DeviceProfileCreate, db: Session = Depends(get_db),
                          current_user: models.User = Security(oauth2.get_current_user, scopes=["tenant"])):
    
    profile_with_name = db.query(models.DeviceProfile).filter(models.DeviceProfile.name == profile.name).all()
    profile_owner_ids = [f.owner_id for f in profile_with_name]
    if current_user.user_id in profile_owner_ids:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"The device profile with name {profile.name} already exists")
    
    new_profile = models.DeviceProfile(owner_id=current_user.user_id, **profile.model_dump())
    
    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)

    return new_profile


@router.get("/profile/all", response_model=List[schemas.DeviceProfileResponse])
def get_all_device_profile(db: Session = Depends(get_db),
                           current_user: models.User = Security(oauth2.get_current_user,
                                                                scopes=["tenant"])):
    profiles = db.query(models.DeviceProfile).filter(models.DeviceProfile.owner_id == current_user.user_id).all()
    return profiles


@router.delete("/{profile_id}", status_code=status.HTTP_200_OK)
def delete_device_profile(profile_id: UUID, db: Session = Depends(get_db),
                current_user: models.User = Security(oauth2.get_current_user, scopes=["tenant"])):
    profile = db.query(models.DeviceProfile).filter(models.DeviceProfile.profile_id == profile_id)
    if profile.first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Profile not found")
    if profile.first().owner_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="You must be the owner of this entity to delete")
    
    profile.delete(synchronize_session=False)
    db.commit()
    
    return Response(status_code=200, content="Successfully deleted device profile")
