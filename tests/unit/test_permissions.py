import pytest
from app.core.permissions import PermissionManager
from app.models.user import User
from tests.fixtures.roles import (
    test_roles,
    test_permissions,
    role_permissions_mapping,
    permission_test_cases,
    role_hierarchy,
    additional_permissions
)

@pytest.fixture
def permission_manager():
    return PermissionManager()

@pytest.fixture
def test_user():
    user = User()
    user.id = 1
    user.email = "test@example.com"
    user.role = "user"
    return user

@pytest.fixture
def admin_user():
    user = User()
    user.id = 2
    user.email = "admin@example.com"
    user.role = "admin"
    return user

def test_role_initialization(permission_manager):
    """Test inicjalizacji ról w systemie."""
    for role in test_roles:
        assert permission_manager.role_exists(role["name"])
        permissions = permission_manager.get_role_permissions(role["name"])
        expected_permissions = role_permissions_mapping.get(role["name"], [])
        assert set(permissions) == set(expected_permissions)

def test_permission_assignment(permission_manager):
    """Test przypisywania uprawnień do ról."""
    for role_name, permissions in role_permissions_mapping.items():
        for permission in permissions:
            assert permission_manager.has_permission(role_name, permission)

@pytest.mark.parametrize("test_case", permission_test_cases)
def test_permission_validation(permission_manager, test_case):
    """Test walidacji uprawnień dla różnych ról."""
    has_permission = permission_manager.has_permission(
        test_case["role"],
        test_case["action"]
    )
    assert has_permission == test_case["should_allow"], test_case["description"]

def test_role_hierarchy(permission_manager):
    """Test hierarchii ról."""
    for role, inherited_roles in role_hierarchy.items():
        for inherited_role in inherited_roles:
            # Sprawdzenie czy rola dziedziczy wszystkie uprawnienia z podrzędnej roli
            parent_permissions = permission_manager.get_role_permissions(role)
            child_permissions = permission_manager.get_role_permissions(inherited_role)
            assert all(perm in parent_permissions for perm in child_permissions)

def test_additional_permissions(permission_manager):
    """Test dodatkowych uprawnień."""
    for permission in additional_permissions:
        assert permission_manager.permission_exists(permission["name"])
        # Sprawdzenie czy uprawnienia są poprawnie przypisane do ról
        for role_name, role_perms in role_permissions_mapping.items():
            if permission["name"] in role_perms:
                assert permission_manager.has_permission(role_name, permission["name"])

def test_user_permissions(permission_manager, test_user, admin_user):
    """Test uprawnień na poziomie użytkownika."""
    # Test uprawnień zwykłego użytkownika
    user_permissions = permission_manager.get_user_permissions(test_user)
    assert set(user_permissions) == set(role_permissions_mapping["user"])
    
    # Test uprawnień admina
    admin_permissions = permission_manager.get_user_permissions(admin_user)
    assert set(admin_permissions) == set(role_permissions_mapping["admin"])

def test_permission_inheritance(permission_manager):
    """Test dziedziczenia uprawnień."""
    # Admin powinien mieć wszystkie uprawnienia moderatora
    moderator_permissions = set(role_permissions_mapping["moderator"])
    admin_permissions = set(role_permissions_mapping["admin"])
    assert moderator_permissions.issubset(admin_permissions)

def test_role_assignment(permission_manager, test_user):
    """Test przypisywania ról użytkownikom."""
    # Zmiana roli użytkownika
    permission_manager.assign_role(test_user, "moderator")
    assert test_user.role == "moderator"
    
    # Sprawdzenie czy użytkownik ma nowe uprawnienia
    new_permissions = permission_manager.get_user_permissions(test_user)
    assert set(new_permissions) == set(role_permissions_mapping["moderator"])

def test_custom_permission_checks(permission_manager, test_user, admin_user):
    """Test niestandardowych sprawdzeń uprawnień."""
    # Test złożonych warunków uprawnień
    test_cases = [
        {
            "user": test_user,
            "action": "users:read",
            "resource": "own_profile",
            "should_allow": True
        },
        {
            "user": test_user,
            "action": "users:write",
            "resource": "other_profile",
            "should_allow": False
        },
        {
            "user": admin_user,
            "action": "users:write",
            "resource": "any_profile",
            "should_allow": True
        }
    ]
    
    for case in test_cases:
        result = permission_manager.check_permission(
            case["user"],
            case["action"],
            case["resource"]
        )
        assert result == case["should_allow"] 