"""empty message

Revision ID: 52061d603b39
Revises: 995ec7f25428
Create Date: 2018-07-19 15:28:26.527526

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '52061d603b39'
down_revision = '995ec7f25428'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('token',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.Column('date_modified', sa.DateTime(), nullable=True),
    sa.Column('deleted', sa.Integer(), nullable=True),
    sa.Column('tid', sa.Integer(), nullable=True),
    sa.Column('symbol', sa.String(length=20), nullable=True),
    sa.Column('name', sa.String(length=50), nullable=True),
    sa.Column('decimal', sa.Integer(), nullable=True),
    sa.Column('contract_address', sa.String(length=255), nullable=True),
    sa.Column('status', sa.Integer(), server_default='-1', nullable=True),
    sa.Column('modified_user_id', sa.Integer(), nullable=True),
    sa.Column('created_user_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['created_user_id'], ['user.id'], ),
    sa.ForeignKeyConstraint(['modified_user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column(u'handshake', sa.Column('token_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'handshake', 'token', ['token_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'handshake', type_='foreignkey')
    op.drop_column(u'handshake', 'token_id')
    op.drop_table('token')
    # ### end Alembic commands ###