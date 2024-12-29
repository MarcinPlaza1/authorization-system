import pytest
from pydantic import ValidationError
from app.models.security import SecurityAuditLogCreate

def test_valid_security_audit_log():
    """Test tworzenia poprawnego logu audytowego."""
    log_data = {
        "event_type": "login_attempt",
        "ip_address": "192.168.1.1",
        "user_agent": "Mozilla/5.0",
        "user_id": 1,
        "details": "Successful login attempt"
    }
    log = SecurityAuditLogCreate(**log_data)
    assert log.event_type == log_data["event_type"]
    assert log.ip_address == log_data["ip_address"]
    assert log.user_agent == log_data["user_agent"]
    assert log.user_id == log_data["user_id"]
    assert log.details == log_data["details"]

def test_security_audit_log_without_optional_fields():
    """Test tworzenia logu audytowego bez opcjonalnych pól."""
    log_data = {
        "event_type": "logout",
        "ip_address": "192.168.1.1",
        "user_agent": "Mozilla/5.0"
    }
    log = SecurityAuditLogCreate(**log_data)
    assert log.event_type == log_data["event_type"]
    assert log.ip_address == log_data["ip_address"]
    assert log.user_agent == log_data["user_agent"]
    assert log.user_id is None
    assert log.details is None

@pytest.mark.parametrize("field,value,expected_error", [
    ("event_type", "a" * 51, "String should have at most 50 characters"),
    ("ip_address", "a" * 46, "String should have at most 45 characters"),
    ("user_agent", "a" * 256, "String should have at most 255 characters"),
    ("details", "a" * 1001, "String should have at most 1000 characters")
])
def test_security_audit_log_field_length_validation(field, value, expected_error):
    """Test walidacji długości pól w logu audytowym."""
    log_data = {
        "event_type": "test_event",
        "ip_address": "192.168.1.1",
        "user_agent": "Mozilla/5.0"
    }
    log_data[field] = value
    
    with pytest.raises(ValidationError) as exc_info:
        SecurityAuditLogCreate(**log_data)
    
    error_dict = exc_info.value.errors()[0]
    assert error_dict["msg"] == expected_error

def test_security_audit_log_required_fields():
    """Test wymaganych pól w logu audytowym."""
    required_fields = ["event_type", "ip_address", "user_agent"]
    
    for field in required_fields:
        log_data = {
            "event_type": "test_event",
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0"
        }
        del log_data[field]
        
        with pytest.raises(ValidationError) as exc_info:
            SecurityAuditLogCreate(**log_data)
        
        error_dict = exc_info.value.errors()[0]
        assert error_dict["type"] == "missing"
        assert field in str(error_dict["loc"]) 