from typing import List, Optional
from uuid import UUID
import json
import datetime

from fastapi import Depends, APIRouter, HTTPException, Security, Response, Body, Query
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, aliased
from sqlalchemy.exc import IntegrityError
from starlette import status
from sqlalchemy import desc

from .. import schemas, models, oauth2
from ..database import get_db
from .user import get_customer_by_id

router = APIRouter(
    prefix="/api/farms",
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
    
    if farm.customer is not None:
        get_customer_by_id(farm.customer.user_id, db, current_user)
        
    new_farm = models.Farm(owner_id=current_user.user_id,
                           name=farm.name,
                           descriptions=farm.descriptions,
                           assigned_customer=farm.customer.user_id if farm.customer else None)
        
    
    db.add(new_farm)
    db.commit()
    db.refresh(new_farm)

    return new_farm


@router.get("/", response_model=List[schemas.FarmResponse])
def get_list_farm(
    db: Session = Depends(get_db),
    current_user: models.User = Security(oauth2.get_current_user, scopes=["tenant", "customer"]),
    _order: str = Query("asc", description="Sorting order: asc or desc", regex="^(asc|desc)$"),
    _sort: str = Query(None, description="Order by a specific field", regex="^[a-zA-Z_]+$")
):
    order_mapping = {
        "name": models.Farm.name,
        "descriptions": models.Farm.descriptions,
        "created_at": models.Farm.created_at,
        "customer": models.User.username,
    }

    default_order_column = models.Farm.created_at
    order_column = order_mapping.get(_sort, default_order_column)

    query = db.query(models.Farm).join(models.User, models.Farm.assigned_customer == models.User.user_id)

    if current_user.role == "tenant":
        query = query.filter(models.Farm.owner_id == current_user.user_id)
    elif current_user.role == "customer":
        query = query.filter(models.Farm.assigned_customer == current_user.user_id)

    if _order == "asc":
        query = query.order_by(order_column)
    else:
        query = query.order_by(order_column.desc())

    farms = query.all()

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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="You have no access to this farm")
        
    return farm
    

@router.patch("/{farm_id}")
def update_farm(farm_id: UUID, new_farm: schemas.FarmCreate, db: Session = Depends(get_db),
                current_user: models.User = Security(oauth2.get_current_user,
                                                    scopes=["tenant"])):
    get_farm_by_id(farm_id, db, current_user)
    farm = db.query(models.Farm).filter(models.Farm.farm_id == farm_id)
    
    update_data = {
        "name": new_farm.name,
        "descriptions": new_farm.descriptions,
        "assigned_customer": new_farm.customer.user_id if new_farm.customer else None
    }
    print(update_data)
    
    farm.update(update_data, synchronize_session=False)

    db.commit()
    return Response(status_code=200, content="Successfully updated farm")


      
@router.delete("/{farm_id}", status_code=status.HTTP_200_OK)
def delete_farm(farm_id: UUID, db: Session = Depends(get_db),
                current_user: models.User = Security(oauth2.get_current_user, scopes=["tenant"])):
    farm = db.query(models.Farm).filter(models.Farm.farm_id == farm_id)
    if farm.first() is None or farm.first().owner_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Farm not found")
    
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

    farm.assigned_customer = customer.user_id
    db.commit()
    return Response(status_code=status.HTTP_200_OK, 
                    content=json.dumps({"detail": "Successfully assigned farm to customer"}),
                    media_type="application/json")


@router.get("/{farm_id}/assets", response_model=List[schemas.AssetResponse])
def get_list_farm_asset_greenhouse(farm_id: UUID, db: Session = Depends(get_db),
                                   current_user: models.User = Security(oauth2.get_current_user,
                                                                        scopes=["tenant", "customer"])):
    farm = get_farm_by_id(farm_id, db, current_user)
    assets = db.query(models.Asset).filter(models.Asset.farm_id == farm_id).all()
    
    return assets


@router.get("/{farm_id}/assets/greenhouses", response_model=List[schemas.AssetResponse])
def get_list_farm_asset_greenhouse(farm_id: UUID, db: Session = Depends(get_db),
                         current_user: models.User = Security(oauth2.get_current_user,
                                                              scopes=["tenant", "customer"])):
    farm = get_farm_by_id(farm_id, db, current_user)
    greenhouses = db.query(models.Asset).filter(models.Asset.farm_id == farm_id, models.Asset.type == "Greenhouse").all()
    
    return greenhouses


@router.get("/{farm_id}/assets/outdoor_fields", response_model=List[schemas.AssetResponse])
def get_list_farm_asset_outdoor_field(farm_id: UUID, db: Session = Depends(get_db),
                         current_user: models.User = Security(oauth2.get_current_user,
                                                              scopes=["tenant", "customer"])):
    farm = get_farm_by_id(farm_id, db, current_user)
    outdoor_fields = db.query(models.Asset).filter(models.Asset.farm_id == farm_id, models.Asset.type == "Outdoor Field").all()
    
    return outdoor_fields

@router.get("/{farm_id}/devices", response_model=List[schemas.DeviceResponse])
def get_list_farm_devices(farm_id: UUID, db: Session = Depends(get_db),
                          current_user: models.User = Security(oauth2.get_current_user,
                                                               scopes=["tenant", "customer"])):
    farm = get_farm_by_id(farm_id, db, current_user)
    devices = (db.query(models.Device).
                  join(models.Asset, models.Device.asset_id == models.Asset.asset_id,
                       isouter=True).
                  filter(models.Asset.farm_id == farm_id).all())
    
    return devices
    

# @router.get("/{farm_id}/telemetry/latest", response_model=List[schemas.TelemetryBase])
# def get_latest_farm_telemetry(farm_id: UUID, db: Session = Depends(get_db), 
#                               current_user: models.User = Security(oauth2.get_current_user, 
#                                                                    scopes=["tenant", "customer"])):
#     farm: models.Farm = get_farm_by_id(farm_id, db, current_user)
    
#     # if current_user.role == "tenant":
#     #     devices = (db.query(models.Device)
#     #                         .join(models.Farm, models.Device.farm_id == models.Farm.farm_id, isouter=True)
#     #                         .filter(models.Farm.owner_id == current_user.user_id).all())
    
#     # telemetry = db.query(models.TimeSeries).join(models.Device,
#     #                                              models.TimeSeries.device_id == models.Device.device_id,
#     #                                              isouter=True).filter(models.Device.farm_id == farm_id).order_by(models.TimeSeries.timestamp.desc()).limit(1).first()
    
    
#     cte = (
#         db.query(
#             models.TimeSeries.key,
#             models.TimeSeries.value,
#             models.Device.farm_id,
#             models.Device.device_id,
#             models.TimeSeries.timestamp,
#             func.row_number().over(partition_by=models.TimeSeries.key, order_by=models.TimeSeries.timestamp.desc()).label('row_num')
#         )
#         .outerjoin(models.Device, models.TimeSeries.device_id == models.Device.device_id)
#         .cte()
#     )

# # Main query to get the latest values for each key
#     query = (
#         db.query(
#             cte.c.key,
#             cte.c.value,
#             cte.c.device_id,
#             cte.c.timestamp
#         )
#         .filter(cte.c.row_num == 1)
#     )

#     result = query.all()
#     return result
