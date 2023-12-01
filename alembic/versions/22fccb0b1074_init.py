"""Init

Revision ID: 22fccb0b1074
Revises: 
Create Date: 2023-11-30 13:49:00.823935

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '22fccb0b1074'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('users',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('username', sa.String(length=100), nullable=False),
    sa.Column('password', sa.String(length=100), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('role', sa.String(length=50), nullable=True),
    sa.PrimaryKeyConstraint('user_id'),
    sa.UniqueConstraint('username')
    )
    op.create_table('device_profiles',
    sa.Column('profile_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('owner_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['owner_id'], ['users.user_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('profile_id')
    )
    op.create_table('farms',
    sa.Column('farm_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('owner_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['owner_id'], ['users.user_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('farm_id')
    )
    op.create_table('devices',
    sa.Column('device_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('is_gateway', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('farm_id', sa.UUID(), nullable=False),
    sa.Column('device_profile_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['device_profile_id'], ['device_profiles.profile_id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['farm_id'], ['farms.farm_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('device_id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('devices')
    op.drop_table('farms')
    op.drop_table('device_profiles')
    op.drop_table('users')
    # ### end Alembic commands ###
