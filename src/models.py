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

    # Add a unique constraint on the combination of username and tenant_id
    __table_args__ = (
        UniqueConstraint('user_id', 'created_by'),
    )
    
    
class TimeSeriesKey(Base):
    __tablename__ = 'ts_keys'
    ts_key_id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Farm(Base):
    __tablename__ = 'farms'
    farm_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    assigned_customer = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=True)
    
#     farm_keys = relationship('TimeSeriesKey', secondary='key_usage')
    
    
# key_usage = Table('key_usages', Base.metadata,
#     Column('farm_id', UUID(as_uuid=True), ForeignKey('farms.farm_id', ondelete="CASCADE")),
#     Column('ts_key_id', UUID(as_uuid=True), ForeignKey('ts_keys.ts_key_id', ondelete="CASCADE")),
#     UniqueConstraint('farm_id', 'ts_key_id')
# )

# class Threshold(Base):
#     __tablename__ = 'thresholds'
#     threshold_id = Column(Integer, primary_key=True)
#     farm_id = Column(UUID(as_uuid=True), ForeignKey("farms.farm_id", ondelete="CASCADE"), nullable=False)
#     key_id = Column(Integer, ForeignKey("keys.ts_key_id", ondelete="CASCADE"), nullable=False)
#     # change the threshold value types when updating ts_value types
#     threshold = Column(Float)
#     created_by = Column(UUID(as_uuid=True), nullable=False)
#     created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


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
    is_gateway = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    farm_id = Column(UUID(as_uuid=True), ForeignKey("farms.farm_id", ondelete="CASCADE"), nullable=False)
    device_profile_id = Column(UUID(as_uuid=True), ForeignKey('device_profiles.profile_id', ondelete="CASCADE"),
                               nullable=False)

    farm = relationship("Farm")
    device_profile = relationship("DeviceProfile")


class TimeSeries(Base):
    __tablename__ = 'ts_values'
    # values currently set as Float and assuming input are valid (not string) until type check update
    value = Column(Float, nullable=False)
    ts_id = Column(Integer, primary_key=True)
    key_id = Column(Integer, ForeignKey('ts_keys.ts_key_id', ondelete="CASCADE"), nullable=False)
    device_id = Column(UUID(as_uuid=True), ForeignKey('devices.device_id', ondelete="CASCADE"), nullable=False)
    device = relationship('Device')
    key = relationship('TimeSeriesKey')
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
