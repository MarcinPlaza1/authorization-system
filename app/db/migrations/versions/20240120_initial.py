"""Initial migration

Revision ID: initial
Create Date: 2024-01-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = 'initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tworzenie tabeli roles
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_roles_id', 'roles', ['id'], unique=False)
    op.create_index('ix_roles_name', 'roles', ['name'], unique=True)

    # Tworzenie tabeli permissions
    op.create_table(
        'permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_permissions_id', 'permissions', ['id'], unique=False)
    op.create_index('ix_permissions_name', 'permissions', ['name'], unique=True)

    # Tworzenie tabeli role_permissions
    op.create_table(
        'role_permissions',
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('permission_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
        sa.PrimaryKeyConstraint('role_id', 'permission_id')
    )

    # Tworzenie tabeli users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_superuser', sa.Boolean(), nullable=True),
        sa.Column('role_id', sa.Integer(), nullable=True),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=True),
        sa.Column('locked_until', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_id', 'users', ['id'], unique=False)
    op.create_index('ix_users_username', 'users', ['username'], unique=True)

    # Tworzenie tabeli revoked_tokens
    op.create_table(
        'revoked_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('jti', sa.String(length=36), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_revoked_tokens_id', 'revoked_tokens', ['id'], unique=False)
    op.create_index('ix_revoked_tokens_jti', 'revoked_tokens', ['jti'], unique=True)
    op.create_index('idx_revoked_tokens_jti_expires', 'revoked_tokens', ['jti', 'expires_at'], unique=False)

    # Tworzenie tabeli password_reset_tokens
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_password_reset_tokens_id', 'password_reset_tokens', ['id'], unique=False)
    op.create_index('ix_password_reset_tokens_token', 'password_reset_tokens', ['token'], unique=True)

    # Tworzenie tabeli password_reset_attempts
    op.create_table(
        'password_reset_attempts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('attempt_time', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_password_reset_attempts_email', 'password_reset_attempts', ['email'], unique=False)
    op.create_index('ix_password_reset_attempts_id', 'password_reset_attempts', ['id'], unique=False)

    # Tworzenie tabeli security_audit_logs
    op.create_table(
        'security_audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=False),
        sa.Column('user_agent', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('details', sa.String(length=1000), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_security_audit_logs_id', 'security_audit_logs', ['id'], unique=False)


def downgrade() -> None:
    op.drop_table('security_audit_logs')
    op.drop_table('password_reset_attempts')
    op.drop_table('password_reset_tokens')
    op.drop_table('revoked_tokens')
    op.drop_table('users')
    op.drop_table('role_permissions')
    op.drop_table('permissions')
    op.drop_table('roles') 