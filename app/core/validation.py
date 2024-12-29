from typing import Dict, Any
import re
from email_validator import validate_email, EmailNotValidError

class DataValidator:
    """Klasa odpowiedzialna za walidację danych wejściowych."""
    
    def __init__(self):
        self.password_pattern = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$')
        self.username_pattern = re.compile(r'^[a-zA-Z0-9_-]{3,32}$')
        self.field_limits = {
            "username": (3, 32),
            "password": (8, 128),
            "full_name": (2, 100),
            "email": (5, 255)
        }
    
    def validate_password(self, password: str) -> bool:
        """Sprawdza, czy hasło spełnia wymagania bezpieczeństwa."""
        if not password:
            return False
        return bool(self.password_pattern.match(password))
    
    def validate_email(self, email: str) -> bool:
        """Sprawdza, czy email jest poprawny."""
        try:
            validate_email(email)
            return True
        except EmailNotValidError:
            return False
    
    def validate_field(self, field: str, value: str) -> bool:
        """Waliduje pole według określonych reguł."""
        if not value:
            return False
            
        if field not in self.field_limits:
            return False
            
        min_length, max_length = self.field_limits[field]
        if not (min_length <= len(value) <= max_length):
            return False
            
        if field == "username":
            return bool(self.username_pattern.match(value))
            
        return True
    
    def validate_format(self, field: str, value: str) -> bool:
        """Waliduje format danych."""
        if field == "phone":
            return bool(re.match(r'^\+?[1-9]\d{1,14}$', value))
        elif field == "postal_code":
            return bool(re.match(r'^\d{2}-\d{3}$', value))
        return True
    
    def validate_field_length(self, field: str, value: str) -> bool:
        """Sprawdza długość pola."""
        if field not in self.field_limits:
            return False
        min_length, max_length = self.field_limits[field]
        return min_length <= len(value) <= max_length
    
    def validate_special_chars(self, field: str, value: str) -> bool:
        """Sprawdza znaki specjalne w polach."""
        if field == "username":
            return not bool(re.search(r'[^a-zA-Z0-9_-]', value))
        elif field == "full_name":
            return not bool(re.search(r'[^a-zA-Z\s]', value))
        elif field == "password":
            return bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', value))
        return True
    
    def validate_registration_data(self, data: Dict[str, Any]) -> bool:
        """Waliduje dane rejestracyjne."""
        required_fields = ["email", "username", "password", "full_name"]
        
        if not all(field in data for field in required_fields):
            return False
            
        if not self.validate_email(data["email"]):
            return False
            
        if not self.validate_password(data["password"]):
            return False
            
        if not self.validate_field("username", data["username"]):
            return False
            
        if not self.validate_field("full_name", data["full_name"]):
            return False
            
        return True
    
    def validate_all_fields(self, data: Dict[str, Any]) -> bool:
        """Waliduje wszystkie pola w danych."""
        for field, value in data.items():
            if not self.validate_field(field, str(value)):
                return False
        return True 