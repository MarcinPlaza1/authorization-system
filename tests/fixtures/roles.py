from typing import Dict, List

# Podstawowe role w systemie
test_roles: List[Dict] = [
    {
        "name": "admin",
        "description": "Administrator systemu"
    },
    {
        "name": "moderator",
        "description": "Moderator treści"
    },
    {
        "name": "user",
        "description": "Standardowy użytkownik"
    }
]

# Uprawnienia dla ról
test_permissions: List[Dict] = [
    {
        "name": "users:read",
        "description": "Przeglądanie użytkowników",
        "resource": "users",
        "action": "read"
    },
    {
        "name": "users:write",
        "description": "Modyfikacja użytkowników",
        "resource": "users",
        "action": "write"
    },
    {
        "name": "users:delete",
        "description": "Usuwanie użytkowników",
        "resource": "users",
        "action": "delete"
    },
    {
        "name": "roles:manage",
        "description": "Zarządzanie rolami",
        "resource": "roles",
        "action": "manage"
    }
]

# Mapowanie uprawnień do ról
role_permissions_mapping = {
    "admin": [
        "users:read",
        "users:write",
        "users:delete",
        "roles:manage"
    ],
    "moderator": [
        "users:read",
        "users:write"
    ],
    "user": [
        "users:read"
    ]
}

# Przypadki testowe dla sprawdzania uprawnień
permission_test_cases = [
    {
        "role": "admin",
        "action": "users:delete",
        "should_allow": True,
        "description": "Admin może usuwać użytkowników"
    },
    {
        "role": "moderator",
        "action": "users:delete",
        "should_allow": False,
        "description": "Moderator nie może usuwać użytkowników"
    },
    {
        "role": "user",
        "action": "users:write",
        "should_allow": False,
        "description": "Użytkownik nie może modyfikować innych użytkowników"
    }
] 

# Dodać do roles.py:

# Hierarchia ról
role_hierarchy = {
    "admin": ["moderator", "user"],
    "moderator": ["user"],
    "user": []
}

# Rozszerzone uprawnienia
additional_permissions = [
    {
        "name": "content:create",
        "description": "Tworzenie treści",
        "resource": "content",
        "action": "create"
    },
    {
        "name": "content:edit",
        "description": "Edycja treści",
        "resource": "content",
        "action": "edit"
    },
    {
        "name": "content:delete",
        "description": "Usuwanie treści",
        "resource": "content",
        "action": "delete"
    }
]

test_permissions.extend(additional_permissions)

# Aktualizacja mapowania uprawnień
role_permissions_mapping.update({
    "admin": role_permissions_mapping["admin"] + [
        "content:create", "content:edit", "content:delete"
    ],
    "moderator": role_permissions_mapping["moderator"] + [
        "content:create", "content:edit"
    ],
    "user": role_permissions_mapping["user"] + [
        "content:create"
    ]
})