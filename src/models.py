import uuid

from sqlalchemy import (Boolean, Column, Integer, String, Table,
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
        UniqueConstraint('username', 'created_by'),
    )

class Farm(Base):
    __tablename__ = 'farms'
    farm_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)

#     assigned_customers = relationship('User', backref='assigned_farm', secondary='farm_assignment')


# farm_assignment = Table('farm_assignment', Base.metadata,
#     Column('farm_id', UUID(as_uuid=True), ForeignKey('farms.farm_id', ondelete="CASCADE")),
#     Column('user_id', UUID(as_uuid=True), ForeignKey('users.user_id', ondelete="CASCADE"))
# )


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


class TimeSeriesKey(Base):
    __tablename__ = 'ts_keys'
    ts_key_id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TimeSeries(Base):
    __tablename__ = 'ts_values'
    value = Column(String, nullable=False)
    ts_id = Column(Integer, primary_key=True)
    key_id = Column(Integer, ForeignKey('ts_keys.ts_key_id', ondelete="CASCADE"), nullable=False)
    device_id = Column(UUID(as_uuid=True), ForeignKey('devices.device_id', ondelete="CASCADE"), nullable=False)
    device = relationship('Device')
    key = relationship('TimeSeriesKey')
    timstamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
