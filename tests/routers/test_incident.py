# test_incident.py
import os
from fastapi.testclient import TestClient
from fastapi import HTTPException, status
from unittest.mock import patch, MagicMock
import pytest
import jwt
from uuid import uuid4
from app.main import app
from app.routers.incident import create_incident_in_database, get_current_user, router as incident_router
from app.schemas.incident import CreateIncidentRequest, CreateIncidentResponse

client = TestClient(app)

SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'secret_key')
ALGORITHM = "HS256"

@pytest.fixture
def mock_get_user_info_request():
    with patch('app.routers.incident.get_user_info_request') as mock:
        yield mock

@pytest.fixture
def mock_create_incident_in_database():
    with patch('app.routers.incident.create_incident_in_database') as mock:
        yield mock

@pytest.fixture
def mock_jwt_encode():
    with patch('jwt.encode') as mock:
        mock.return_value = 'mocked_token'
        yield mock

def create_test_token():
    token_data = {
        "sub": str(uuid4()),
        "user_type": "company"
    }
    return jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

def test_create_incident_success(mock_get_user_info_request, mock_create_incident_in_database):
    
    token_data = {
        "sub": str(str(uuid4())),
        "user_type": "company"
    }
    
    token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)  
    user_id = str(uuid4())
    company_id = str(uuid4())
    incident_id = str(uuid4())
    
    mock_get_user_info_request.return_value = ({"user_data": "valid"}, 200)
    mock_create_incident_in_database.return_value = (
        {
            "id": incident_id,
            "user_id": user_id,
            "company_id": company_id,
            "description": "Test incident",
            "state": "open",
            "channel": "phone",
            "priority": "medium",
            "creation_date": "2023-01-01T00:00:00"
        },
        201
    )

    response = client.post(
        "/incident-command-receptor/",
        json={
            "user_id": user_id,
            "company_id": company_id,
            "description": "Test incident",
            "state": "open",
            "channel": "phone",
            "priority": "medium"
        },
        headers={"authorization": token}
    )

    print(f"Response status code: {response.status_code}")
    print(f"Response content: {response.content}")

    assert response.status_code == 201, f"Expected 201, but got {response.status_code}. Response: {response.content}"

def test_create_incident_user_not_found(mock_get_user_info_request):
    token = create_test_token()
    mock_get_user_info_request.return_value = ({"detail": "User not found"}, 404)

    response = client.post(
        "/incident-command-receptor/",
        json={
            "user_id": str(uuid4()),
            "company_id": str(uuid4()),
            "description": "Test incident",
            "state": "open",
            "channel": "phone",
            "priority": "medium"
        },
        headers={"authorization": token}
    )

    assert response.status_code == 404

def test_create_incident_both_services_fail(
    mock_get_user_info_request, mock_create_incident_in_database
):
    token = create_test_token()
    mock_get_user_info_request.return_value = ({"user_data": "valid"}, 200)
    mock_create_incident_in_database.return_value = ({"error": "Service unavailable"}, 503)

    response = client.post(
        "/incident-command-receptor/",
        json={
            "user_id": str(uuid4()),
            "company_id": str(uuid4()),
            "description": "Test incident",
            "state": "open",
            "channel": "phone",
            "priority": "medium"
        },
        headers={"authorization": token}
    )

    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "Service unavailable"

@pytest.mark.parametrize("invalid_data, expected_status", [
    ({"user_id": "invalid-uuid", "company_id": str(uuid4()), "description": "Test", "state": "open", "channel": "phone", "priority": "medium"}, 422),
    ({"user_id": str(uuid4()), "company_id": "invalid-uuid", "description": "Test", "state": "open", "channel": "phone", "priority": "medium"}, 422),
    ({"user_id": str(uuid4()), "company_id": str(uuid4()), "description": "Test", "state": "invalid", "channel": "phone", "priority": "medium"}, 422),
    ({"user_id": str(uuid4()), "company_id": str(uuid4()), "description": "Test", "state": "open", "channel": "invalid", "priority": "medium"}, 422),
    ({"user_id": str(uuid4()), "company_id": str(uuid4()), "description": "Test", "state": "open", "channel": "phone", "priority": "invalid"}, 422),
])
def test_create_incident_invalid_input(invalid_data, expected_status, mock_get_user_info_request):
    token = create_test_token()
    mock_get_user_info_request.return_value = ({"user_data": "valid"}, 200)

    response = client.post("/incident-command-receptor/", json=invalid_data, headers={"token": token})

    assert response.status_code == expected_status

@patch('requests.post')
def test_create_incident_in_database(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": str(uuid4())}
    mock_response.status_code = 201
    mock_post.return_value = mock_response

    incident_data = {
        "user_id": uuid4(),
        "company_id": uuid4(),
        "description": "Test incident",
        "state": "open",
        "channel": "phone",
        "priority": "medium"
    }
    token = create_test_token()

    response_data, status_code = create_incident_in_database(incident_data, token)

    assert status_code == 201
    assert "id" in response_data
    mock_post.assert_called_once()
