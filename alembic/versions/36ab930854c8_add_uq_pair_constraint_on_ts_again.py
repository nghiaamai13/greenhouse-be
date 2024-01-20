"""Add UQ pair constraint on TS Again

Revision ID: 36ab930854c8
Revises: 8d957af0b34c
Create Date: 2024-01-17 16:08:09.678115

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '36ab930854c8'
down_revision: Union[str, None] = '8d957af0b34c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('ts_values')
    op.create_table('ts_values_latest',
    sa.Column('value', sa.Float(), nullable=False),
    sa.Column('ts_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('key', sa.String(), nullable=False),
    sa.Column('device_id', sa.UUID(), nullable=False),
    sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['devices.device_id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['key'], ['ts_keys.ts_key'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('ts_id'),
    sa.UniqueConstraint('device_id', 'key', name='uq_ts_device_key_pair')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('ts_values_latest')
    op.create_table('ts_values')
    # ### end Alembic commands ###
