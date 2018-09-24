"""empty message

Revision ID: 79df2fb3e8a9
Revises: 6a5565cc6771
Create Date: 2018-09-24 14:52:33.697529

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '79df2fb3e8a9'
down_revision = '6a5565cc6771'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('handshake', 'is_private')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('handshake', sa.Column('is_private', mysql.INTEGER(display_width=11), server_default=sa.text(u"'0'"), autoincrement=False, nullable=True))
    # ### end Alembic commands ###
