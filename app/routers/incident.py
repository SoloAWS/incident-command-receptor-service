# router.py
from fastapi import APIRouter, File, Form, HTTPException, Depends, Header, UploadFile
from ..schemas.incident import CreateIncidentRequest, CreateIncidentResponse, IncidentChannel, IncidentPriority, IncidentState
import requests
import os
import jwt
import json
from uuid import UUID
from typing import Optional, Tuple

router = APIRouter(prefix="/incident-command", tags=["Incident Command"])

USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:8002/user")
INCIDENT_SERVICE_URL_MAIN = os.getenv("INCIDENT_SERVICE_URL_MAIN", "http://192.168.68.111:8004/incident-command-main")
INCIDENT_SERVICE_URL_REDUNDANT = os.getenv("INCIDENT_SERVICE_URL_REDUNDANT", "http://192.168.68.111:8005/incident-command-backup")

SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'secret_key')
ALGORITHM = "HS256"

def get_user_info_request(user_id: UUID, token: str):
    api_url = USER_SERVICE_URL
    endpoint = f"/user/{user_id}"
    headers = {"token": f"{token}"}
    response = requests.get(f"{api_url}{endpoint}", headers=headers)
    return response.json(), response.status_code

def get_current_user(token: str = Header(None)):
    if token is None:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        return json.JSONEncoder.default(self, obj)

def create_incident_in_database(incident_data: dict, token: str, url: str) -> Tuple[dict, int]:
    endpoint = "/"
    headers = {
        "token": f"{token}",
        "Content-Type": "application/json"
    }
    try:
        json_data = json.dumps(incident_data, cls=UUIDEncoder)
        response = requests.post(f"{url}{endpoint}", headers=headers, data=json_data, timeout=5)
        
        return response.json(), response.status_code
    except requests.RequestException:
        return {"error": "Service unavailable"}, 503
    
def create_incident_in_database_user(incident_data: dict, token: str, url: str, file: Optional[UploadFile] = None) -> Tuple[dict, int]:
    endpoint = "/user-incident"
    headers = {
        "token": f"{token}",
    }
    try:     
        form_data = {
            "user_id": str(incident_data['user_id']),
            "company_id": str(incident_data['company_id']),
            "description": incident_data['description'],
            "state": incident_data['state'],
            "channel": incident_data['channel'],
            "priority": incident_data['priority']
        }

        files = None
        if file:
            files = {"file": (file.filename, file.file, file.content_type)}
        
        response = requests.post(f"{url}{endpoint}", headers=headers, data=form_data, files=files, timeout=5)
        
        return response.json(), response.status_code
    except requests.RequestException:
        return {"error": "Service unavailable"}, 503

@router.post("/", response_model=CreateIncidentResponse, status_code=201)
async def create_incident(
    incident: CreateIncidentRequest,
    current_user: dict = Depends(get_current_user)
):
    token = jwt.encode(current_user, SECRET_KEY, algorithm=ALGORITHM)
    incident_data = incident.dict()
    
    user_data, user_status = get_user_info_request(incident.user_id, token)
    if user_status != 200:
        raise HTTPException(status_code=user_status, detail=user_data)

    # Try main database service
    response_data, status_code = create_incident_in_database(incident_data, token, INCIDENT_SERVICE_URL_MAIN)
    
    # If main service fails, try redundant service
    if status_code >= 500:
        response_data, status_code = create_incident_in_database(incident_data, token, INCIDENT_SERVICE_URL_REDUNDANT)
    
    if status_code != 201:
        raise HTTPException(status_code=status_code, detail=response_data)
    
    return CreateIncidentResponse(**response_data)

@router.post("/user-incident", response_model=CreateIncidentResponse, status_code=201)
async def create_user_incident(
    user_id: UUID = Form(...),
    company_id: UUID = Form(...),
    description: str = Form(...),
    state: str = Form(IncidentState.OPEN.value),
    channel: str = Form(IncidentChannel.MOBILE.value),
    priority: str = Form(IncidentPriority.MEDIUM.value),
    file: Optional[UploadFile] = File(None),
    #current_user: dict = Depends(get_current_user)
):
    #token = jwt.encode(current_user, SECRET_KEY, algorithm=ALGORITHM)
    
    incident_data = {
        "user_id": user_id,
        "company_id": company_id,
        "description": description,
        "state": state,
        "channel": channel,
        "priority": priority
    }

    # Try main database service
    response_data, status_code = create_incident_in_database_user(incident_data, 'token', INCIDENT_SERVICE_URL_MAIN, file)
    
    # If main service fails, try redundant service
    if status_code >= 500:
        response_data, status_code = create_incident_in_database_user(incident_data, 'token', INCIDENT_SERVICE_URL_REDUNDANT, file)
    
    if status_code != 201:
        raise HTTPException(status_code=status_code, detail=response_data)
    
    return CreateIncidentResponse(**response_data)