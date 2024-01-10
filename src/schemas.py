from datetime import datetime
from typing import Optional, List
from uuid import UUID
from enum import Enum
from pydantic import BaseModel, validator

# USER
class UserBase(BaseModel):
    username: str
    password: str


class Roles(str, Enum):
    TENANT = 'tenant'

    
class TenantCreate(UserBase):
    role: Roles = Roles.TENANT

    
class UserCreate(UserBase):
    pass
    

class UserResponse(BaseModel):
    user_id: UUID
    username: str
    created_at: datetime
    role: str
    created_by: UUID


# FARM
class FarmBase(BaseModel):
    name: str
    descriptions: Optional[str] = None
#    assigned_customer: Optional[UUID] = None


class FarmCreate(FarmBase):
    customer: Optional[UserResponse] = None
    
    class Config:
        from_attributes = True


class FarmResponse(FarmBase):
    farm_id: UUID
    created_at: datetime
    descriptions: Optional[str] = None
    customer: Optional[UserResponse] = None

    owner: UserResponse
    class Config:
        from_attributes = True


# ASSET
class AssetType(str, Enum):
    OUTDOOR_FIELD = 'Outdoor Field'
    GREENHOUSE = 'Greenhouse'


class AssetBase(BaseModel):
    name: str
    type: AssetType    


class AssetCreate(AssetBase):
    farm_id: UUID

    
class AssetResponse(AssetBase):
    asset_id: UUID
    created_at: datetime
    owner_id: UUID
    farm_id: UUID
    farm: FarmResponse        
    
    class Config:
        from_attributes = True
        
class TSKeyBase(BaseModel):
    ts_key: str

class DeviceProfileBase(BaseModel):
    name: str


class DeviceProfileCreate(DeviceProfileBase):
    pass


class DeviceProfileResponse(DeviceProfileBase):
    profile_id: UUID
    owner_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class DeviceBase(BaseModel):
    name: str
    label: Optional[str] = None
    is_gateway: bool = False


class DeviceCreate(DeviceBase):
    asset_id: UUID
    device_profile_id: UUID


class DeviceResponse(DeviceBase):
    device_id: UUID
    label: Optional[str] = None
    created_at: datetime
    asset_id: UUID
    device_profile_id: UUID
    asset: AssetResponse
    device_profile: DeviceProfileResponse

    class Config:
        from_attributes = True


class TelemetryBase(BaseModel):
    key: str
    value: float
    timestamp: datetime
    device_id: UUID

    
class Token(BaseModel):
    access_token: str
    token_type: str
    scope: str

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[str] = None
    scope: str 
    
