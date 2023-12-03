"""Add some null constraints

Revision ID: f8a66c5dbd59
Revises: b2e3a1433e26
Create Date: 2023-12-03 14:31:51.933581

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8a66c5dbd59'
down_revision: Union[str, None] = 'b2e3a1433e26'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('ts_keys', 'key',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.create_unique_constraint(None, 'ts_keys', ['key'])
    op.alter_column('ts_values', 'value',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.alter_column('users', 'role',
               existing_type=sa.VARCHAR(length=50),
               nullable=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('users', 'role',
               existing_type=sa.VARCHAR(length=50),
               nullable=True)
    op.alter_column('ts_values', 'value',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.drop_constraint(None, 'ts_keys', type_='unique')
    op.alter_column('ts_keys', 'key',
               existing_type=sa.VARCHAR(),
               nullable=True)
    # ### end Alembic commands ###
