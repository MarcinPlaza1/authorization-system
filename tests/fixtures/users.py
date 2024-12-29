from typing import Dict, List

# Przykładowi użytkownicy do testów
test_users: List[Dict] = [
    {
        "email": "admin@example.com",
        "username": "admin",
        "password": "Admin123!@#",
        "full_name": "Admin User",
        "is_active": True,
        "is_superuser": True
    },
    {
        "email": "user@example.com",
        "username": "regularuser",
        "password": "User123!@#",
        "full_name": "Regular User",
        "is_active": True,
        "is_superuser": False
    },
    {
        "email": "inactive@example.com",
        "username": "inactiveuser",
        "password": "Inactive123!@#",
        "full_name": "Inactive User",
        "is_active": False,
        "is_superuser": False
    }
]

# Dane do testów rejestracji
valid_registration_data = {
    "email": "newuser@example.com",
    "username": "newuser",
    "password": "NewUser123!@#",
    "full_name": "New Test User"
}

invalid_registration_data = [
    {
        "email": "invalid-email",
        "username": "user1",
        "password": "Pass123!@#",
        "full_name": "Invalid Email User"
    },
    {
        "email": "user@example.com",
        "username": "sh",  # za krótka nazwa
        "password": "Pass123!@#",
        "full_name": "Short Username User"
    },
    {
        "email": "user@example.com",
        "username": "valid_username",
        "password": "short",  # za słabe hasło
        "full_name": "Weak Password User"
    }
]

# Dane do testów logowania
login_test_cases = [
    {
        "credentials": {"username": "admin@example.com", "password": "Admin123!@#"},
        "expected_status": 200,
        "description": "Valid admin login"
    },
    {
        "credentials": {"username": "wrong@example.com", "password": "WrongPass123!"},
        "expected_status": 401,
        "description": "Invalid credentials"
    },
    {
        "credentials": {"username": "inactive@example.com", "password": "Inactive123!@#"},
        "expected_status": 400,
        "description": "Inactive user login attempt"
    }
] 

# Dodać do users.py:

# Przypadki testowe dla walidacji hasła
password_validation_cases = [
    {
        "password": "short",
        "should_pass": False,
        "description": "Za krótkie hasło"
    },
    {
        "password": "nouppercase123!",
        "should_pass": False,
        "description": "Brak wielkich liter"
    },
    {
        "password": "NOLOWERCASE123!",
        "should_pass": False,
        "description": "Brak małych liter"
    },
    {
        "password": "NoSpecialChars123",
        "should_pass": False,
        "description": "Brak znaków specjalnych"
    },
    {
        "password": "Valid@Password123",
        "should_pass": True,
        "description": "Poprawne hasło"
    }
]

# Przypadki testowe dla walidacji email
email_validation_cases = [
    {
        "email": "invalid.email",
        "should_pass": False,
        "description": "Brak domeny"
    },
    {
        "email": "@example.com",
        "should_pass": False,
        "description": "Brak nazwy użytkownika"
    },
    {
        "email": "valid@example.com",
        "should_pass": True,
        "description": "Poprawny email"
    }
]

# Dane do testów aktualizacji profilu
profile_update_test_cases = [
    {
        "current_data": test_users[1],  # regularuser
        "update_data": {
            "full_name": "Updated Name",
            "password": "NewPass123!@#"
        },
        "should_succeed": True,
        "description": "Poprawna aktualizacja profilu"
    },
    {
        "current_data": test_users[2],  # inactive user
        "update_data": {
            "full_name": "Try Update"
        },
        "should_succeed": False,
        "description": "Próba aktualizacji nieaktywnego konta"
    }
]