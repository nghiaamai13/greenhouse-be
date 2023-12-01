import uuid

from sqlalchemy import Boolean, Column, Integer, String, func, DateTime, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = 'users'
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    role = Column(String(50), default="customer")


class Farm(Base):
    __tablename__ = 'farms'
    farm_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)


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

#
# class TimeSeriesKey(Base):
#     __tablename__ = 'ts_keys'
#     key = Column(String(100), primary_key=True)
#     key_id = Column(Integer, nullable=False, unique=True, autoincrement=True)
#
#
# class TimeSeries(Base):
#     __tablename__ = 'ts_values_latest'
#     id = Column(Integer, primary_key=True)
#     device_id = Column(UUID(as_uuid=True), ForeignKey('devices.device_id', ondelete="CASCADE"), nullable=False)
#     key = Column(String(100), ForeignKey('ts_keys.key', ondelete="CASCADE"), nullable=False)
#     timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
#     int_val = Column(BigInteger)

