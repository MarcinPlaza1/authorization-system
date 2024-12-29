"""add rbac permissions

Revision ID: add_rbac_permissions
Revises: 
Create Date: 2024-01-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = 'add_rbac_permissions'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Tworzenie tabeli permissions
    op.create_table(
        'permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.String(255)),
        sa.Column('resource', sa.String(50), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index('ix_permissions_name', 'permissions', ['name'])

    # Tworzenie tabeli role_permissions
    op.create_table(
        'role_permissions',
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('permission_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('role_id', 'permission_id')
    )

    # Tworzenie tabeli role_hierarchy
    op.create_table(
        'role_hierarchy',
        sa.Column('parent_role_id', sa.Integer(), nullable=False),
        sa.Column('child_role_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['parent_role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['child_role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('parent_role_id', 'child_role_id')
    )

    # Dodanie podstawowych uprawnień
    op.execute("""
        INSERT INTO permissions (name, description, resource, action) VALUES
        ('user_create', 'Create new users', 'users', 'create'),
        ('user_read', 'Read user information', 'users', 'read'),
        ('user_update', 'Update user information', 'users', 'update'),
        ('user_delete', 'Delete users', 'users', 'delete'),
        ('role_manage', 'Manage roles and permissions', 'roles', 'manage')
    """)

def downgrade():
    op.drop_table('role_hierarchy')
    op.drop_table('role_permissions')
    op.drop_index('ix_permissions_name')
    op.drop_table('permissions') 