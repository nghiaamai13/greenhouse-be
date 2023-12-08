from uuid import UUID

from fastapi import Depends, APIRouter, HTTPException
from sqlalchemy.orm import Session
from starlette import status

from .. import models
from ..database import get_db

router = APIRouter(
    prefix="/api/telemetry",
    tags=["Telemetry"]
)

@router.post("/telemetry/{device_id}", status_code=status.HTTP_201_CREATED)
def post_telemetry(device_id: UUID, db: Session = Depends(get_db),
                   data: dict = None):
    device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    
    if data is None or data == {}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="No data received")
    
    for key, value in data.items():
        existing_key = db.query(models.TimeSeriesKey).filter(models.TimeSeriesKey.key == key).first()
        if not existing_key:
            new_key = models.TimeSeriesKey(key=key)
            db.add(new_key)
            db.commit()
            db.refresh(new_key)
            print(f"Inserted new key: {new_key}")
        else:
            new_key = existing_key
        telemetry_data = models.TimeSeries(
            key_id=new_key.ts_key_id,
            device_id=device_id,
            value=float(value),
        )
        db.add(telemetry_data)
        db.commit()
        
    print(f"Received telemetry data from device with id: {device_id}")

