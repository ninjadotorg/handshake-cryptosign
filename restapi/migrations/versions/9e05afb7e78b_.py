"""empty message

Revision ID: 9e05afb7e78b
Revises: 86a8cf01a358
Create Date: 2018-12-06 11:47:01.368615

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9e05afb7e78b'
down_revision = '86a8cf01a358'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('source', sa.Column('image_url', sa.String(length=512), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('source', 'image_url')
    # ### end Alembic commands ###
