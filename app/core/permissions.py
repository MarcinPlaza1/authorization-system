from typing import List, Dict, Any, Optional
from app.models.user import User

class PermissionManager:
    """Klasa zarządzająca uprawnieniami w systemie."""
    
    def __init__(self):
        self._roles = {
            "admin": {
                "description": "Administrator systemu",
                "permissions": [
                    "users:read", "users:write", "users:delete",
                    "roles:manage", "content:create", "content:edit",
                    "content:delete"
                ]
            },
            "moderator": {
                "description": "Moderator treści",
                "permissions": [
                    "users:read", "users:write",
                    "content:create", "content:edit"
                ]
            },
            "user": {
                "description": "Standardowy użytkownik",
                "permissions": ["users:read", "content:create"]
            }
        }
        
        self._role_hierarchy = {
            "admin": ["moderator", "user"],
            "moderator": ["user"],
            "user": []
        }
    
    def role_exists(self, role_name: str) -> bool:
        """Sprawdza czy rola istnieje."""
        return role_name in self._roles
    
    def get_role_permissions(self, role_name: str) -> List[str]:
        """Pobiera listę uprawnień dla danej roli."""
        if not self.role_exists(role_name):
            return []
            
        permissions = set(self._roles[role_name]["permissions"])
        
        # Dodaj uprawnienia z ról podrzędnych
        for inherited_role in self._role_hierarchy.get(role_name, []):
            permissions.update(self.get_role_permissions(inherited_role))
            
        return list(permissions)
    
    def has_permission(self, role_name: str, permission: str) -> bool:
        """Sprawdza czy rola ma dane uprawnienie."""
        return permission in self.get_role_permissions(role_name)
    
    def permission_exists(self, permission_name: str) -> bool:
        """Sprawdza czy uprawnienie istnieje w systemie."""
        for role_data in self._roles.values():
            if permission_name in role_data["permissions"]:
                return True
        return False
    
    def get_user_permissions(self, user: User) -> List[str]:
        """Pobiera listę uprawnień dla użytkownika."""
        return self.get_role_permissions(user.role)
    
    def assign_role(self, user: User, role_name: str) -> bool:
        """Przypisuje rolę do użytkownika."""
        if not self.role_exists(role_name):
            return False
        user.role = role_name
        return True
    
    def check_permission(self, user: User, action: str, resource: str) -> bool:
        """Sprawdza uprawnienia użytkownika do wykonania akcji na zasobie."""
        if not user.is_active:
            return False
            
        if user.is_superuser:
            return True
            
        user_permissions = self.get_user_permissions(user)
        
        # Sprawdź uprawnienia do własnego profilu
        if resource == "own_profile" and action == "users:read":
            return True
            
        # Sprawdź standardowe uprawnienia
        required_permission = f"{resource}:{action}"
        return required_permission in user_permissions 