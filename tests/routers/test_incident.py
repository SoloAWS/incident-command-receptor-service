import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from uuid import UUID
from app.main import app
from app.routers.incident import router as incident_command_router, create_incident_in_database, get_user_info_request


client = TestClient(app)

@pytest.fixture
def mock_get_user_info_request():
    with patch('app.routers.incident.get_user_info_request') as mock:
        yield mock

@pytest.fixture
def mock_create_incident_in_database():
    with patch('app.routers.incident.create_incident_in_database') as mock:
        yield mock

def test_create_incident_success(mock_get_user_info_request, mock_create_incident_in_database):
    mock_get_user_info_request.return_value = ({"user_data": "valid"}, 200)
    mock_create_incident_in_database.return_value = (
        {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "user_id": "123e4567-e89b-12d3-a456-426614174001",
            "company_id": "123e4567-e89b-12d3-a456-426614174002",
            "description": "Test incident",
            "state": "open",
            "channel": "phone",
            "priority": "medium",
            "creation_date": "2023-01-01T00:00:00"
        },
        201
    )

    response = client.post(
        "/incident-command/",
        json={
            "user_id": "123e4567-e89b-12d3-a456-426614174001",
            "company_id": "123e4567-e89b-12d3-a456-426614174002",
            "description": "Test incident",
            "state": "open",
            "channel": "phone",
            "priority": "medium"
        }
    )
    
    assert response.status_code == 201
    
    response_json = response.json()
    print(f"Response JSON: {response_json}")
    


def test_create_incident_user_not_found(mock_get_user_info_request):
    mock_get_user_info_request.return_value = ({"detail": "User not found"}, 404)

    response = client.post(
        "/incident-command/",
        json={
            "user_id": "123e4567-e89b-12d3-a456-426614174001",
            "company_id": "123e4567-e89b-12d3-a456-426614174002",
            "description": "Test incident",
            "state": "open",
            "channel": "phone",
            "priority": "medium"
        }
    )

    print(f"Response status code: {response.status_code}")
    print(f"Response content: {response.content}")

    assert response.status_code == 404

def test_create_incident_main_service_fails_redundant_succeeds(
    mock_get_user_info_request, mock_create_incident_in_database
):
    mock_get_user_info_request.return_value = ({"user_data": "valid"}, 200)
    mock_create_incident_in_database.side_effect = [
        ({"error": "Service unavailable"}, 503),
        (
            {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "company_id": "123e4567-e89b-12d3-a456-426614174002",
                "description": "Test incident",
                "state": "open",
                "channel": "phone",
                "priority": "medium",
                "creation_date": "2023-01-01T00:00:00"
            },
            201
        )
    ]

    response = client.post(
        "/incident-command/",
        json={
            "user_id": "123e4567-e89b-12d3-a456-426614174001",
            "company_id": "123e4567-e89b-12d3-a456-426614174002",
            "description": "Test incident",
            "state": "open",
            "channel": "phone",
            "priority": "medium"
        }
    )

    assert response.status_code == 201
    assert response.json()["id"] == "123e4567-e89b-12d3-a456-426614174000"
    assert mock_create_incident_in_database.call_count == 2

def test_create_incident_both_services_fail(
    mock_get_user_info_request, mock_create_incident_in_database
):
    mock_get_user_info_request.return_value = ({"user_data": "valid"}, 200)
    mock_create_incident_in_database.return_value = ({"error": "Service unavailable"}, 503)

    response = client.post(
        "/incident-command/",
        json={
            "user_id": "123e4567-e89b-12d3-a456-426614174001",
            "company_id": "123e4567-e89b-12d3-a456-426614174002",
            "description": "Test incident",
            "state": "open",
            "channel": "phone",
            "priority": "medium"
        }
    )

    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "Service unavailable"
    assert mock_create_incident_in_database.call_count == 2

@pytest.mark.parametrize("invalid_data, expected_status", [
    ({"user_id": "invalid-uuid", "company_id": "123e4567-e89b-12d3-a456-426614174002", "description": "Test", "state": "open", "channel": "phone", "priority": "medium"}, 422),
    ({"user_id": "123e4567-e89b-12d3-a456-426614174001", "company_id": "invalid-uuid", "description": "Test", "state": "open", "channel": "phone", "priority": "medium"}, 422),
    ({"user_id": "123e4567-e89b-12d3-a456-426614174001", "company_id": "123e4567-e89b-12d3-a456-426614174002", "description": "Test", "state": "invalid", "channel": "phone", "priority": "medium"}, 422),
    ({"user_id": "123e4567-e89b-12d3-a456-426614174001", "company_id": "123e4567-e89b-12d3-a456-426614174002", "description": "Test", "state": "open", "channel": "invalid", "priority": "medium"}, 422),
    ({"user_id": "123e4567-e89b-12d3-a456-426614174001", "company_id": "123e4567-e89b-12d3-a456-426614174002", "description": "Test", "state": "open", "channel": "phone", "priority": "invalid"}, 422),
])
def test_create_incident_invalid_input(invalid_data, expected_status, mock_get_user_info_request):
    mock_get_user_info_request.return_value = ({"user_data": "valid"}, 200)

    response = client.post("/incident-command/", json=invalid_data)

    print(f"Response status code: {response.status_code}")
    print(f"Response content: {response.content}")
    assert response.status_code == expected_status

@patch('requests.post')
def test_create_incident_in_database(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "123e4567-e89b-12d3-a456-426614174000"}
    mock_response.status_code = 201
    mock_post.return_value = mock_response

    incident_data = {
        "user_id": UUID("123e4567-e89b-12d3-a456-426614174001"),
        "company_id": UUID("123e4567-e89b-12d3-a456-426614174002"),
        "description": "Test incident",
        "state": "open",
        "channel": "phone",
        "priority": "medium"
    }
    token = "test_token"
    url = "http://test-url.com"

    response_data, status_code = create_incident_in_database(incident_data, token, url)

    assert status_code == 201
    assert response_data == {"id": "123e4567-e89b-12d3-a456-426614174000"}
    mock_post.assert_called_once()

@patch('requests.get')
def test_get_user_info_request(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {"user_data": "valid"}
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    user_id = UUID("123e4567-e89b-12d3-a456-426614174001")
    token = "test_token"

    response_data, status_code = get_user_info_request(user_id, token)

    assert status_code == 200
    assert response_data == {"user_data": "valid"}
    mock_get.assert_called_once()