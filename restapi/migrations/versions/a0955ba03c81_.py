"""empty message

Revision ID: a0955ba03c81
Revises: c9837711a468
Create Date: 2018-07-10 14:02:08.998950

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a0955ba03c81'
down_revision = 'c9837711a468'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('source', sa.Column('url', sa.String(length=255), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('source', 'url')
    # ### end Alembic commands ###
