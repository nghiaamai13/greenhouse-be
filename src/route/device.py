import json
from typing import List
from uuid import UUID
from sqlalchemy.orm import aliased
from sqlalchemy import func

from fastapi import Depends, APIRouter, HTTPException, Security, Response, Query
from sqlalchemy.orm import Session
from starlette import status

from .. import schemas, models, oauth2, mqtt
from ..database import get_db

router = APIRouter( 
    prefix="/api",
    tags=["Device"]
)


@router.post("/devices", status_code=status.HTTP_201_CREATED, response_model=schemas.DeviceResponse)
def create_device(device: schemas.DeviceCreate, db: Session = Depends(get_db),
                  current_user: models.User = Security(oauth2.get_current_user, scopes=["tenant"])):
    
    asset_query = db.query(models.Asset).filter(models.Asset.asset_id == device.asset_id, 
                                                models.Asset.owner_id == current_user.user_id)
    asset = asset_query.first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    device_profile_query = db.query(models.DeviceProfile).filter(models.DeviceProfile.profile_id == device.device_profile_id,
                                                          models.DeviceProfile.owner_id == current_user.user_id)
    device_profile = device_profile_query.first()
    if not device_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device profile not found")

    same_device_name = db.query(models.Device).filter(models.Device.name == device.name).all()
    asset_ids = [dev.asset_id for dev in same_device_name]
    if device.asset_id in asset_ids:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"The device with name {device.name} already exists in this asset")     
    
    new_device = models.Device(**device.model_dump())
    db.add(new_device)
    db.commit()
    db.refresh(new_device)
    mqtt.mqtt_subscriber.subscribe_all()
    return new_device


@router.get('/devices', response_model=List[schemas.DeviceResponse])
def get_list_devices(
    db: Session = Depends(get_db),
    current_user: models.User = Security(oauth2.get_current_user, scopes=["tenant", "customer"]),
    _order: str = Query("asc", description="Sorting order: asc or desc", regex="^(asc|desc)$"),
    _sort: str = Query(None, description="Order by a specific field", regex="^[a-zA-Z_]+$")
):
    order_mapping = {
        "name": models.Device.name,
        "label": models.Device.label,
        "asset": models.Asset.name,
        "device_profile": models.DeviceProfile.name,
        "created_at": models.Device.created_at,
    }

    default_order_column = models.Device.created_at
    order_column = order_mapping.get(_sort, default_order_column)

    devices_query = (
        db.query(models.Device)
        .join(models.Asset, models.Device.asset_id == models.Asset.asset_id, isouter=True)
        .join(models.DeviceProfile, models.Device.device_profile_id == models.DeviceProfile.profile_id, isouter=True)
    )

    if current_user.role == "tenant":
        devices_query = devices_query.filter(models.Asset.owner_id == current_user.user_id)
    else:
        devices_query = devices_query.join(models.Farm, models.Asset.farm_id == models.Farm.farm_id, isouter=True)
        devices_query = devices_query.filter(models.Farm.assigned_customer == current_user.user_id)

    if _order == "asc":
        devices_query = devices_query.order_by(order_column)
    else:
        devices_query = devices_query.order_by(order_column.desc())

    devices = devices_query.all()

    return devices


@router.get("/devices/{device_id}", response_model=schemas.DeviceResponse)
def get_device_by_id(device_id: UUID, db: Session = Depends(get_db),
                     current_user: models.User = Security(oauth2.get_current_user,
                                                          scopes=["tenant", "customer"])):
    try:
        device, tenant_id, customer_id = (db.query(models.Device, models.Farm.owner_id, models.Farm.assigned_customer)
                                            .join(models.Asset, models.Device.asset_id == models.Asset.asset_id, isouter=True)
                                            .join(models.Farm, models.Asset.farm_id == models.Farm.farm_id, isouter=True)
                                            .filter(models.Device.device_id == device_id).first())
    except TypeError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    
    print(device, tenant_id, customer_id)
    
    if tenant_id == current_user.user_id or customer_id == current_user.user_id:
        return device
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Device not found")

#patch device
@router.patch("/devices/{device_id}", status_code=status.HTTP_200_OK)
def update_device(device_id: UUID, new_device: schemas.DeviceCreate, db: Session = Depends(get_db),
                  current_user: models.User = Security(oauth2.get_current_user,
                                                       scopes=["tenant"])):
    get_device_by_id(device_id, db, current_user)
    device = db.query(models.Device).filter(models.Device.device_id == device_id)
    
    update_data = {
        "name": new_device.name,
        "asset_id": new_device.asset_id,
        "device_profile_id": new_device.device_profile_id
    }
    
    device.update(update_data, synchronize_session=False)

    db.commit()
    return Response(status_code=200, content="Successfully updated device")



#delete device 
@router.delete("/devices/{device_id}", status_code=status.HTTP_200_OK)
def delete_device(device_id: UUID, db: Session = Depends(get_db),
                  current_user: models.User = Security(oauth2.get_current_user, 
                                                      scopes = ["tenant"])):
    device = db.query(models.Device).filter(models.Device.device_id == device_id)
    if device.first() is None or device.first().asset.farm.owner_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Device not found")
    
    device.delete(synchronize_session=False)
    db.commit()
    
    return Response(status_code=200, content="Successfully deleted device")

    
@router.post("/device_profiles", status_code=status.HTTP_201_CREATED,
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


@router.get("/device_profiles", response_model=List[schemas.DeviceProfileResponse])
def get_list_device_profile(
    db: Session = Depends(get_db),
    current_user: models.User = Security(oauth2.get_current_user, scopes=["tenant"]),
    _order: str = Query("asc", description="Sorting order: asc or desc", regex="^(asc|desc)$"),
    _sort: str = Query(None, description="Order by a specific field", regex="^[a-zA-Z_]+$")
):
    order_mapping = {
        "name": models.DeviceProfile.name,  
        "created_at": models.DeviceProfile.created_at,  
    }

    default_order_column = models.DeviceProfile.created_at 
    order_column = order_mapping.get(_sort, default_order_column)

    if _order == "asc":
        profiles = db.query(models.DeviceProfile).filter(models.DeviceProfile.owner_id == current_user.user_id).order_by(order_column).all()
    else:
        profiles = db.query(models.DeviceProfile).filter(models.DeviceProfile.owner_id == current_user.user_id).order_by(order_column.desc()).all()

    return profiles


@router.delete("/device_profiles/{profile_id}", status_code=status.HTTP_200_OK)
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


@router.get("/devices/{device_id}/telemetry/latest", response_model=List[schemas.TelemetryBase])
def get_latest_device_telemetry(device_id: UUID, db: Session = Depends(get_db), 
                              current_user: models.User = Security(oauth2.get_current_user, 
                                                                   scopes=["tenant", "customer"])):
    device: models.Device = get_device_by_id(device_id, db, current_user)

    ts_alias = aliased(models.TimeSeries)
    
    cte = (
        db.query(
            models.TimeSeries.key,
            models.TimeSeries.device_id,
            ts_alias.value,
            ts_alias.timestamp,
            func.row_number().over(
                partition_by=models.TimeSeries.key,
                order_by=models.TimeSeries.timestamp.desc()
            ).label('row_num')
        )
        .join(ts_alias, models.TimeSeries.key == ts_alias.key)
        .filter(models.TimeSeries.device_id == device_id)
        .cte(name="latest_telemetry")
    )

    query = (
        db.query(cte.c.key, cte.c.value, cte.c.timestamp, cte.c.device_id)
        .filter(cte.c.row_num == 1)
    )
    print(query.all())

    return query.all()