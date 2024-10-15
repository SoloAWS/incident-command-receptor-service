# router.py
from fastapi import APIRouter, HTTPException, Depends
from ..schemas.incident import CreateIncidentRequest, CreateIncidentResponse
import requests
import os
import jwt
from typing import Tuple

router = APIRouter(prefix="/incident-command", tags=["Incident Command"])

INCIDENT_SERVICE_URL_MAIN = os.getenv("INCIDENT_SERVICE_URL_MAIN", "http://localhost:8004/incident-command-main")
INCIDENT_SERVICE_URL_REDUNDANT = os.getenv("INCIDENT_SERVICE_URL_REDUNDANT", "http://localhost:8005/incident-command-backup")

SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'secret_key')
ALGORITHM = "HS256"

def get_current_user(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def create_incident_in_database(incident_data: dict, token: str, url: str) -> Tuple[dict, int]:
    endpoint = "/"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(f"{url}{endpoint}", headers=headers, json=incident_data, timeout=5)
        return response.json(), response.status_code
    except requests.RequestException:
        return {"error": "Service unavailable"}, 503

@router.post("/incidents", response_model=CreateIncidentResponse)
async def create_incident(
    incident: CreateIncidentRequest,
    current_user: dict = Depends(get_current_user)
):
    token = jwt.encode(current_user, SECRET_KEY, algorithm=ALGORITHM)
    incident_data = incident.dict()

    # Try main database service
    response_data, status_code = create_incident_in_database(incident_data, token, INCIDENT_SERVICE_URL_MAIN)
    
    # If main service fails, try redundant service
    if status_code >= 500:
        response_data, status_code = create_incident_in_database(incident_data, token, INCIDENT_SERVICE_URL_REDUNDANT)
    
    if status_code != 201:
        raise HTTPException(status_code=status_code, detail=response_data)
    
    return CreateIncidentResponse(**response_data)