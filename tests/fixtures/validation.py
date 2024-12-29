from typing import Dict, List

# Walidacja danych wejściowych
input_validation_test_cases = [
    {
        "field": "username",
        "value": "a",
        "should_pass": False,
        "description": "Za krótka nazwa użytkownika"
    },
    {
        "field": "username",
        "value": "valid_username123",
        "should_pass": True,
        "description": "Poprawna nazwa użytkownika"
    },
    {
        "field": "full_name",
        "value": "",
        "should_pass": False,
        "description": "Puste pełne imię"
    }
]

# Walidacja formatu danych
data_format_test_cases = [
    {
        "field": "phone",
        "value": "+48123456789",
        "should_pass": True,
        "description": "Poprawny format telefonu"
    },
    {
        "field": "postal_code",
        "value": "12-345",
        "should_pass": True,
        "description": "Poprawny kod pocztowy"
    }
]
