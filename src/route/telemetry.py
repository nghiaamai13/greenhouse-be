from uuid import UUID

from fastapi import APIRouter, Depends, Security
from sqlalchemy.orm import Session
from starlette import status
from datetime import datetime, timezone

from .. import models, oauth2
from ..database import get_db
from ..cassandra_db import get_cassandra_session

router = APIRouter( 
    prefix="/api",
    tags=["Telemetry"]
)

# @router.post("/telemetry/{device_id}", status_code=status.HTTP_201_CREATED)
# def post_telemetry(device_id: UUID, db: Session = Depends(get_db),
#                    data: dict = None):
#     device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
#     #current_farm = db.query(models.Farm).filter(models.Farm.farm_id == device.farm_id).first()

#     if not device:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    
#     if data is None or data == {}:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
#                             detail="No data received")
    
#     for key, value in data.items():
#         add_ts_postgres(device, key, value, db)
        
#     print(f"Received telemetry datas from device with id: {device_id}")


def add_ts_postgres(device_id: str, key, value, db: Session):
    device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
    existing_key = db.query(models.TimeSeriesKey).filter(models.TimeSeriesKey.ts_key == key).first()
    if not existing_key:
        new_key = models.TimeSeriesKey(ts_key=key)
        db.add(new_key)
        db.commit()
        db.refresh(new_key)
    # existing key    
    else:
        new_key = existing_key
        #check for threshold
        existing_threshold = db.query(models.Threshold).filter(models.Threshold.asset_id == device.asset_id,
                                                               models.Threshold.key == new_key.ts_key).first()
        if existing_threshold:
            if float(value) < existing_threshold.threshold_min or float(value) > existing_threshold.threshold_max:
                print(f"Threshold exceeded for key: '{key}' on device: {device.device_id} value: {value} threshold_min: {existing_threshold.threshold_min} threshold_max: {existing_threshold.threshold_max}")

        else:
            print(f"No threshold set for this '{key}' key")
    # add new key to asset table
    current_asset = db.query(models.Asset).filter(models.Asset.asset_id == device.asset_id).first()
    if new_key not in current_asset.asset_keys:
        current_asset.asset_keys.append(new_key)
        db.commit()
        print(f"Added key: '{key}' on asset: {current_asset.name} id: {current_asset.asset_id}")
    
    # add or update latest telemetry
    existing_ts = db.query(models.TimeSeries).filter_by(device_id=device.device_id, key=key).first()
    if existing_ts:
        existing_ts.value = float(value)
        existing_ts.timestamp = datetime.now()
        db.commit()
        print(f"Updated value {value} for key: '{key}' on device: {device.device_id}")
    
    else:    
        ts_data = models.TimeSeries(
            key=new_key.ts_key,
            device_id=device.device_id,
            value=float(value),
        )
        
        db.add(ts_data)
        db.commit()
        print(f"Added ts for key: '{key}' on device: {device.device_id}")

    
def add_ts_cassandra(device_id: str, key, value):
    db = get_cassandra_session()

    timestamp = datetime.utcnow().replace(tzinfo=timezone.utc)
    models.TSCassandra.create(key=key, device_id=device_id, value=float(value), created_at=timestamp)

    print(f"Saved telemetry data to Cassandra: Device: {device_id}, Key: '{key}', Value: {value}")

@router.get("/telemetry/count")
def count_all_telemetry(db: Session = Depends(get_db), current_user: models.User = Security(oauth2.get_current_user, scopes=["tenant", "customer"])):
    join = db.query(models.Device).join(models.Asset, models.Device.asset_id == models.Asset.asset_id, isouter=True).join(models.Farm, models.Asset.farm_id == models.Farm.farm_id, isouter=True)
    if current_user.role == "tenant":
        devices_query = join.filter(models.Farm.owner_id == current_user.user_id)
    else:
        devices_query = join.filter(models.Farm.assigned_customer == current_user.user_id)

    device_ids = [str(device.device_id) for device in devices_query.all()]
        
    try:
        cassandra_session = get_cassandra_session()
        count_query = f"SELECT COUNT(*) FROM {models.TSCassandra.__keyspace__}.{models.TSCassandra.__table_name__} WHERE device_id IN ({','.join(device_ids)});"
        count_result = cassandra_session.execute(count_query)
        return count_result.one()['count'] if count_result else 0

    finally:
        cassandra_session.shutdown()
    
    