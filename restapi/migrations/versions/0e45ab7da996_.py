"""empty message

Revision ID: 0e45ab7da996
Revises: d1fc63ce0983
Create Date: 2018-10-14 23:38:49.061647

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0e45ab7da996'
down_revision = 'd1fc63ce0983'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('match', sa.Column('grant_permission', sa.Integer(), server_default='0', nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('match', 'grant_permission')
    # ### end Alembic commands ###
