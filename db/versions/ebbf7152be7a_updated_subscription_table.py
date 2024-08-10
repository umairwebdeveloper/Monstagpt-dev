"""updated subscription table

Revision ID: ebbf7152be7a
Revises: bd908fbe392b
Create Date: 2024-07-09 12:38:20.311606

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ebbf7152be7a'
down_revision = 'bd908fbe392b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('subscriptions', sa.Column('subscription_started', sa.Integer(), nullable=True))
    op.drop_index('ix_subscriptions_subscription_ends', table_name='subscriptions')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index('ix_subscriptions_subscription_ends', 'subscriptions', ['subscription_ends'], unique=False)
    op.drop_column('subscriptions', 'subscription_started')
    # ### end Alembic commands ###
