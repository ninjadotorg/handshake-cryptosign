"""empty message

Revision ID: 4877a8b7eee3
Revises: 2ccb40667695
Create Date: 2018-06-12 15:46:32.480684

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4877a8b7eee3'
down_revision = '2ccb40667695'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('free_bet', sa.Integer(), server_default='0', nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user', 'free_bet')
    # ### end Alembic commands ###
