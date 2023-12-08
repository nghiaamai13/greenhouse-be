from datetime import datetime
from typing import Optional, List
from uuid import UUID
from enum import Enum
from pydantic import BaseModel, validator


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


class FarmBase(BaseModel):
    name: str


class FarmCreate(FarmBase):
    pass


class FarmResponse(FarmBase):
    farm_id: UUID
    created_at: datetime
    owner_id: UUID
    assigned_customer: Optional[UUID] = None

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
    is_gateway: bool = False


class DeviceCreate(DeviceBase):
    farm_id: UUID
    device_profile_id: UUID


class DeviceResponse(DeviceBase):
    device_id: UUID
    created_at: datetime
    farm: FarmResponse
    device_profile: DeviceProfileResponse

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[str] = None
    scope: str
