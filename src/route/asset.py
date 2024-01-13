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
router = APIRouter(
    prefix="/api/assets",
    tags=["Assets"]
)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.AssetResponse)
def create_asset(asset: schemas.AssetCreate,
                 db: Session = Depends(get_db),
                 current_user: models.User = Security(oauth2.get_current_user,
                                                     scopes=["tenant"])):
    asset_with_name = db.query(models.Asset).filter(models.Asset.name == asset.name).all()
    farm_ids = [asset.farm_id for asset in asset_with_name]
    farm_query = db.query(models.Farm).filter(models.Farm.farm_id == asset.farm_id, models.Farm.owner_id == current_user.user_id)
    if farm_query.first().farm_id in farm_ids:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Asset with this name already exists in  {farm_query.first().name}")
    
    new_asset = models.Asset(owner_id=current_user.user_id, **asset.model_dump())
    db.add(new_asset)
    db.commit()
    db.refresh(new_asset)
    return new_asset

@router.get("/", response_model=List[schemas.AssetResponse])
def get_list_asset(
    db: Session = Depends(get_db),
    current_user: models.User = Security(oauth2.get_current_user, scopes=["tenant", "customer"]),
    _order: str = Query("asc", description="Sorting order: asc or desc", regex="^(asc|desc)$"),
    _sort: str = Query(None, description="Order by a specific field", regex="^[a-zA-Z_]+$")
):
    # Validate and sanitize input values if necessary

    # Define a dictionary to map the query parameter to the actual column in the database
    order_mapping = {
        "name": models.Asset.name,
        "type": models.Asset.type,
        "created_at": models.Asset.created_at,
        "": models.Farm.name,
        # Add more fields as needed
    }

    # Determine the column to order by
    default_order_column = models.Asset.created_at  # Change this to your default field
    order_column = order_mapping.get(_sort, default_order_column)

    # Apply sorting order and join conditions
    if current_user.role == "tenant":
        assets_query = db.query(models.Asset).filter(models.Asset.owner_id == current_user.user_id)
    elif current_user.role == "customer":
        assets_query = (
            db.query(models.Asset)
            .join(models.Farm, models.Asset.farm_id == models.Farm.farm_id, isouter=True)
            .filter(models.Farm.assigned_customer == current_user.user_id)
        )
        
    if _sort == "":
        assets_query = assets_query.join(models.Farm, models.Asset.farm_id == models.Farm.farm_id, isouter=True)

    if _order == "asc":
        assets_query = assets_query.order_by(order_column)
    else:
        assets_query = assets_query.order_by(order_column.desc())

    assets = assets_query.all()

    return assets


@router.get("/{asset_id}", response_model=schemas.AssetResponse)
def get_asset_by_id(asset_id: UUID, db: Session = Depends(get_db),
                   current_user: models.User = Security(oauth2.get_current_user,
                                                        scopes=["tenant", "customer"])):
    asset = db.query(models.Asset).filter(models.Asset.asset_id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Asset not found")
    customer_id = asset.farm.customer.user_id    
    if asset.owner_id != current_user.user_id and customer_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Asset not found")    
    
    return asset

@router.patch("/{asset_id}")
def update_asset(asset_id: UUID, new_asset: schemas.AssetCreate, db: Session = Depends(get_db),
                current_user: models.User = Security(oauth2.get_current_user,
                                                    scopes=["tenant"])):
    get_asset_by_id(asset_id, db, current_user)
    asset = db.query(models.Asset).filter(models.Asset.asset_id == asset_id)
    
    
    update_data = {
        "name": new_asset.name,
        "type": new_asset.type,
        "farm_id": new_asset.farm_id
    }
    
    asset.update(update_data, synchronize_session=False)

    db.commit()
    return Response(status_code=200, content="Successfully updated asset")
   
@router.delete("/{asset_id}", status_code=status.HTTP_200_OK)
def delete_asset(asset_id: UUID, db: Session = Depends(get_db),
                current_user: models.User = Security(oauth2.get_current_user,
                                                     scopes=["tenant"])):
    asset = db.query(models.Asset).filter(models.Asset.asset_id == asset_id)
    if asset.first() is None or asset.first().owner_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Asset not found")
    
    asset.delete(synchronize_session=False)
    db.commit()
    
    return Response(status_code=200, content="Successfully deleted an asset")


@router.get("/{asset_id}/devices", response_model=List[schemas.DeviceResponse])
def get_list_asset_devices(asset_id: UUID, db: Session = Depends(get_db),
                           current_user: models.User = Security(oauth2.get_current_user,
                                                               scopes=["tenant", "customer"])):
    get_asset_by_id(asset_id, db, current_user)
    devices = db.query(models.Device).filter(models.Device.asset_id == asset_id).all()
    
    return devices


@router.get("/{asset_id}/keys", response_model=List[schemas.TSKeyBase])
def get_list_asset_keys(asset_id: UUID, db: Session = Depends(get_db),
                      current_user: models.User = Security(oauth2.get_current_user,
                                                          scopes=["tenant", "customer"])):
    asset = get_asset_by_id(asset_id, db, current_user)
    return asset.asset_keys
    
    
@router.get("/{asset_id}/thresholds")
def get_thresholds_of_asset(asset_id: UUID, db: Session = Depends(get_db),
                           current_user: models.User = Security(oauth2.get_current_user,
                                                                  scopes=["tenant", "customer"])):
    get_asset_by_id(asset_id, db, current_user)
    thresholds = db.query(models.Threshold).filter(models.Threshold.asset_id==asset_id).all()

    return thresholds
    
    
@router.post("/{asset_id}/threshold/{key}")
def set_asset_threshold_on_key(asset_id: UUID, key: str,
                              threshold_data: dict = Body(...),
                              db: Session = Depends(get_db),
                              current_user: models.User = Security(oauth2.get_current_user,
                                                              scopes=["tenant", "customer"])):
    asset: models.Asset = get_asset_by_id(asset_id, db, current_user)
    valid_keys = [key.ts_key for key in asset.asset_keys]
    
    if key not in valid_keys:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Invalid asset key")
        
    threshold_max = threshold_data.get('threshold_max')
    threshold_min = threshold_data.get('threshold_min')
    
    if threshold_min >= threshold_max:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Max value must be larger than min value")
     
    existing_threshold = db.query(models.Threshold).filter(models.Threshold.asset_id==asset_id,
                                                              models.Threshold.key==key).first()
    if existing_threshold:
        existing_threshold.threshold_max = threshold_max
        existing_threshold.threshold_min = threshold_min
        existing_threshold.modified_by = current_user.user_id
        existing_threshold.modified_at = datetime.datetime.now()
    
    else:    
        new_threshold = models.Threshold(asset_id=asset_id, key=key,
                                        threshold_max=threshold_max, threshold_min=threshold_min,
                                        modified_by=current_user.user_id)
        
        db.add(new_threshold)
    
    db.commit()

    return existing_threshold if existing_threshold else new_threshold


@router.put("/{asset_id}/threshold/{key}")
def update_asset_threshold_on_key(asset_id: UUID, key: str,
                                 new_max_value: float = None,
                                 new_min_value: float = None,
                                 db: Session = Depends(get_db),
                                 current_user: models.User = Security(oauth2.get_current_user,
                                                                  scopes=["tenant", "customer"])):
    
    existing_threshold = db.query(models.Threshold).filter(models.Threshold.asset_id==asset_id,
                                                           models.Threshold.key==key).first()
    
    if not existing_threshold:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Threshold not found, create it first")
        
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


@router.delete("/{asset_id}/threshold/{key}")
def delete_asset_threshold_with_key(asset_id: UUID, key: str,
                                   db: Session = Depends(get_db),
                                   current_user: models.User = Security(oauth2.get_current_user,
                                                                 scopes=["tenant", "customer"])):
    
    get_asset_by_id(asset_id, db, current_user)
    existing_threshold = db.query(models.Threshold).filter(models.Threshold.asset_id==asset_id,
                                                           models.Threshold.key==key)
    if not existing_threshold.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail={"Threshold not found for the specified asset and key"})
    
    existing_threshold.delete(synchronize_session=False)
    
    db.commit()

    return Response(status_code=200, content=f"Successfully deleted {key} threshold")

@router.get("/{asset_id}/telemetry/latest", response_model=List[schemas.AssetTelemetry])
def get_latest_asset_telemetry(asset_id: UUID, db: Session = Depends(get_db), 
                              current_user: models.User = Security(oauth2.get_current_user, 
                                                                   scopes=["tenant", "customer"])):
    asset: models.Asset = get_asset_by_id(asset_id, db, current_user)
    
    # if current_user.role == "tenant":
    #     devices = (db.query(models.Device)
    #                         .join(models.Farm, models.Device.asset_id == models.Farm.asset_id, isouter=True)
    #                         .filter(models.Farm.owner_id == current_user.user_id).all())
    
    # telemetry = db.query(models.TimeSeries).join(models.Device,
    #                                              models.TimeSeries.device_id == models.Device.device_id,
    #                                              isouter=True).filter(models.Device.asset_id == asset_id).order_by(models.TimeSeries.timestamp.desc()).limit(1).first()
    
    
    cte = (
        db.query(
            models.TimeSeries.key,
            models.TimeSeries.value,
            models.Device.asset_id,
            models.Device.device_id,
            models.Device.name.label('device_name'),
            models.TimeSeries.timestamp,
            func.row_number().over(partition_by=models.TimeSeries.key, order_by=models.TimeSeries.timestamp.desc()).label('row_num')
        )
        .filter(models.Device.asset_id == asset_id)
        .outerjoin(models.Device, models.TimeSeries.device_id == models.Device.device_id)
        .cte()
    )

    query = (
        db.query(
            cte.c.key,
            cte.c.value,
            cte.c.device_id,
            cte.c.timestamp,
            cte.c.device_name
        )
        .filter(cte.c.row_num == 1)
    )

    result = query.all()
    print(result)
    return result
