"""customer_id

Revision ID: 3b194bc2bf10
Revises: 
Create Date: 2024-07-04 15:25:14.540085

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3b194bc2bf10'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('customer_id', sa.String(length=128), nullable=True))
    op.drop_index('ix_users_payment_id', table_name='users')
    op.create_index(op.f('ix_users_customer_id'), 'users', ['customer_id'], unique=False)
    op.drop_column('users', 'payment_id')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('payment_id', sa.VARCHAR(length=128), autoincrement=False, nullable=True))
    op.drop_index(op.f('ix_users_customer_id'), table_name='users')
    op.create_index('ix_users_payment_id', 'users', ['payment_id'], unique=False)
    op.drop_column('users', 'customer_id')
    # ### end Alembic commands ###
