"""empty message

Revision ID: ec7f9015e5af
Revises: c82554d504aa
Create Date: 2018-11-19 10:59:56.056732

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'ec7f9015e5af'
down_revision = 'c82554d504aa'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('redeem', sa.Column('reserved_id', sa.Integer(), server_default='0', nullable=True))
    op.drop_column('redeem', 'is_issued')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('redeem', sa.Column('is_issued', mysql.INTEGER(display_width=11), server_default=sa.text(u"'0'"), autoincrement=False, nullable=True))
    op.drop_column('redeem', 'reserved_id')
    # ### end Alembic commands ###
