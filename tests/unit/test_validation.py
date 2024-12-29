import pytest
from app.core.validation import DataValidator
from tests.fixtures.validation import input_validation_test_cases, data_format_test_cases
from tests.fixtures.users import (
    password_validation_cases,
    email_validation_cases,
    invalid_registration_data
)

@pytest.fixture
def validator():
    return DataValidator()

@pytest.mark.parametrize("test_case", password_validation_cases)
def test_password_validation(validator, test_case):
    """Test walidacji haseł z różnymi przypadkami."""
    result = validator.validate_password(test_case["password"])
    assert result == test_case["should_pass"], test_case["description"]

@pytest.mark.parametrize("test_case", email_validation_cases)
def test_email_validation(validator, test_case):
    """Test walidacji adresów email."""
    result = validator.validate_email(test_case["email"])
    assert result == test_case["should_pass"], test_case["description"]

@pytest.mark.parametrize("test_case", input_validation_test_cases)
def test_input_validation(validator, test_case):
    """Test walidacji różnych pól wejściowych."""
    result = validator.validate_field(
        test_case["field"],
        test_case["value"]
    )
    assert result == test_case["should_pass"], test_case["description"]

@pytest.mark.parametrize("test_case", data_format_test_cases)
def test_data_format_validation(validator, test_case):
    """Test walidacji formatów danych."""
    result = validator.validate_format(
        test_case["field"],
        test_case["value"]
    )
    assert result == test_case["should_pass"], test_case["description"]

def test_registration_data_validation(validator):
    """Test walidacji danych rejestracyjnych."""
    for invalid_data in invalid_registration_data:
        result = validator.validate_registration_data(invalid_data)
        assert result is False, f"Powinno odrzucić nieprawidłowe dane: {invalid_data}"

@pytest.mark.parametrize("field,min_length,max_length", [
    ("username", 3, 32),
    ("password", 8, 128),
    ("full_name", 2, 100),
    ("email", 5, 255)
])
def test_field_length_validation(validator, field, min_length, max_length):
    """Test walidacji długości pól."""
    # Test za krótkiej wartości
    too_short = "a" * (min_length - 1)
    assert not validator.validate_field_length(field, too_short)
    
    # Test prawidłowej długości
    valid_length = "a" * (min_length + 1)
    assert validator.validate_field_length(field, valid_length)
    
    # Test za długiej wartości
    too_long = "a" * (max_length + 1)
    assert not validator.validate_field_length(field, too_long)

def test_special_characters_validation(validator):
    """Test walidacji znaków specjalnych."""
    invalid_chars = [
        ("username", "user@name"),  # @ niedozwolony w nazwie użytkownika
        ("full_name", "Name#123"),  # cyfry i znaki specjalne w imieniu
        ("password", "password"),   # brak znaków specjalnych w haśle
    ]
    
    for field, value in invalid_chars:
        assert not validator.validate_special_chars(field, value)

def test_combined_validation(validator):
    """Test łączonej walidacji wielu pól."""
    test_data = {
        "username": "valid_user",
        "email": "valid@example.com",
        "password": "ValidPass123!@#",
        "full_name": "Valid Name"
    }
    
    assert validator.validate_all_fields(test_data)
    
    # Test z jednym nieprawidłowym polem
    invalid_data = test_data.copy()
    invalid_data["email"] = "invalid-email"
    assert not validator.validate_all_fields(invalid_data) 