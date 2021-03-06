"""empty message

Revision ID: 140378bd9be7
Revises: 3e8b6518c8d1
Create Date: 2018-12-27 16:47:24.887112

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '140378bd9be7'
down_revision = '3e8b6518c8d1'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('tx', sa.Column('onchain_task_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'tx', 'onchain_task', ['onchain_task_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'tx', type_='foreignkey')
    op.drop_column('tx', 'onchain_task_id')
    # ### end Alembic commands ###
