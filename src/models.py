import uuid
from sqlalchemy import (Boolean, Column, Integer, String, Float, Table,
                        func, DateTime, ForeignKey, UniqueConstraint)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    __tablename__ = 'users'
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    role = Column(String(50), default="customer", nullable=False)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    __table_args__ = (
        UniqueConstraint('user_id', 'created_by'),
    )
    
class TimeSeriesKey(Base):
    __tablename__ = 'ts_keys'
    ts_key = Column(String, primary_key=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Farm(Base):
    __tablename__ = 'farms'
    farm_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    descriptions = Column(String(250))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)    
    assigned_customer = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    owner = relationship('User', foreign_keys=[owner_id], primaryjoin="Farm.owner_id == User.user_id")
    customer = relationship('User', foreign_keys=[assigned_customer], primaryjoin="Farm.assigned_customer == User.user_id")

#     farm_keys = relationship('TimeSeriesKey', secondary='key_usages')
    
# key_usages = Table('key_usages', Base.metadata,
#     Column('farm_id', UUID(as_uuid=True), ForeignKey('farms.farm_id', ondelete="CASCADE")),
#     Column('ts_key', String, ForeignKey('ts_keys.ts_key', ondelete="CASCADE")),
#     UniqueConstraint('farm_id', 'ts_key')
# )


class Asset(Base):
    __tablename__ = 'assets'
    asset_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    type = Column(String(100), nullable=False)
    farm_id = Column(UUID(as_uuid=True), ForeignKey("farms.farm_id", ondelete="CASCADE"), nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)    

    asset_keys = relationship('TimeSeriesKey', secondary='key_usages')
    farm = relationship('Farm')
    
key_usages = Table('key_usages', Base.metadata,
    Column('asset_id', UUID(as_uuid=True), ForeignKey('assets.asset_id', ondelete="CASCADE")),
    Column('ts_key', String, ForeignKey('ts_keys.ts_key', ondelete="CASCADE")),
    UniqueConstraint('asset_id', 'ts_key')
)   


class Threshold(Base):
    __tablename__ = 'thresholds'
    threshold_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.asset_id", ondelete="CASCADE"), nullable=False)
    key = Column(String, ForeignKey("ts_keys.ts_key", ondelete="CASCADE"), nullable=False)
    # TODO: change the threshold value types when updating ts_value types
    threshold_max = Column(Float)
    threshold_min = Column(Float)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    modified_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    __table_args__ = (
        UniqueConstraint('asset_id', 'key', name='uq_farm_key_pair'),
    )

class DeviceProfile(Base):
    __tablename__ = 'device_profiles'
    profile_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)


class Device(Base):
    __tablename__ = 'devices'
    device_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    label = Column(String(100))
    is_gateway = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.asset_id", ondelete="CASCADE"), nullable=False)
    device_profile_id = Column(UUID(as_uuid=True), ForeignKey('device_profiles.profile_id', ondelete="CASCADE"),
                               nullable=False)

    asset = relationship("Asset")
    device_profile = relationship("DeviceProfile")


class TimeSeries(Base):
    __tablename__ = 'ts_values'
    # values currently set as Float and assuming input are valid (not string) until type check update
    value = Column(Float, nullable=False)
    ts_id = Column(Integer, primary_key=True)
    key = Column(String, ForeignKey('ts_keys.ts_key', ondelete="CASCADE"), nullable=False)
    device_id = Column(UUID(as_uuid=True), ForeignKey('devices.device_id', ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
