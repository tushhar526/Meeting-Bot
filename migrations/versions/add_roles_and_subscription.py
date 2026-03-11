"""Add roles and subscription management

Revision ID: add_roles_and_subscription
Revises: e8250b97fd1f
Create Date: 2026-03-10 18:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'add_roles_and_subscription'
down_revision = 'e8250b97fd1f'
branch_labels = None
depends_on = None


def upgrade():
    # Create plans table
    op.create_table('plans',
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('plan_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('max_meetings', sa.Integer(), nullable=True),
        sa.Column('max_users', sa.Integer(), nullable=True),
        sa.Column('features', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('plan_id'),
        sa.UniqueConstraint('name')
    )

    # Add new columns to users table
    op.add_column('users', sa.Column('organization_name', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('role', sa.String(length=50), nullable=False, server_default='admin'))
    op.add_column('users', sa.Column('plan_id', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('subscription_status', sa.String(length=50), nullable=False, server_default='inactive'))
    op.add_column('users', sa.Column('subscription_start_date', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('subscription_end_date', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=True, server_default='1'))
    op.add_column('users', sa.Column('is_deleted', sa.Boolean(), nullable=True, server_default='0'))
    op.add_column('users', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('updated_at', sa.DateTime(), nullable=True))

    # Update existing columns
    op.alter_column('users', 'username', 
                    existing_type=sa.VARCHAR(),
                    type_=sa.String(length=100),
                    nullable=False)
    op.alter_column('users', 'email', 
                    existing_type=sa.VARCHAR(),
                    type_=sa.String(length=255),
                    nullable=False)

    # Add foreign key constraint
    op.create_foreign_key('fk_users_plan_id', 'users', 'plans', ['plan_id'], ['plan_id'])

    # Insert default plans
    op.execute("""
        INSERT INTO plans (name, plan_type, description, price, max_meetings, max_users, features, is_active, created_at, updated_at) VALUES
        ('Free Plan', 'free', 'Basic free plan with limited features', 0.00, 10, 1, '["Basic meeting features", "10 meetings/month"]', true, NOW(), NOW()),
        ('Basic Plan', 'basic', 'Basic plan for small teams', 29.99, 100, 5, '["All free features", "100 meetings/month", "5 users", "Priority support"]', true, NOW(), NOW()),
        ('Pro Plan', 'pro', 'Professional plan for growing teams', 99.99, 1000, 20, '["All basic features", "1000 meetings/month", "20 users", "Advanced analytics", "API access"]', true, NOW(), NOW()),
        ('Enterprise Plan', 'enterprise', 'Enterprise plan for large organizations', 299.99, None, None, '["All pro features", "Unlimited meetings", "Unlimited users", "Custom integrations", "Dedicated support"]', true, NOW(), NOW())
    """)

    # Set created_at and updated_at for existing users
    op.execute("UPDATE users SET created_at = NOW(), updated_at = NOW() WHERE created_at IS NULL")


def downgrade():
    # Remove foreign key constraint
    op.drop_constraint('fk_users_plan_id', 'users', type_='foreignkey')
    
    # Remove new columns from users table
    op.drop_column('users', 'updated_at')
    op.drop_column('users', 'created_at')
    op.drop_column('users', 'deleted_at')
    op.drop_column('users', 'is_deleted')
    op.drop_column('users', 'is_active')
    op.drop_column('users', 'subscription_end_date')
    op.drop_column('users', 'subscription_start_date')
    op.drop_column('users', 'subscription_status')
    op.drop_column('users', 'plan_id')
    op.drop_column('users', 'role')
    op.drop_column('users', 'organization_name')

    # Revert column changes
    op.alter_column('users', 'email', 
                    existing_type=sa.String(length=255),
                    type_=sa.VARCHAR(),
                    nullable=False)
    op.alter_column('users', 'username', 
                    existing_type=sa.String(length=100),
                    type_=sa.VARCHAR(),
                    nullable=False)

    # Drop plans table
    op.drop_table('plans')
