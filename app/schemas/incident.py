# schemas.py
from pydantic import BaseModel, Field
from uuid import UUID
from enum import Enum
from typing import Optional

class IncidentState(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"
    ESCALATED = "escalated"

class IncidentChannel(str, Enum):
    PHONE = "phone"
    EMAIL = "email"
    CHAT = "chat"
    MOBILE = "mobile"

class IncidentPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class CreateIncidentRequest(BaseModel):
    user_id: UUID
    company_id: UUID
    manager_id: Optional[UUID] = None
    description: str
    state: IncidentState = Field(default=IncidentState.OPEN)
    channel: IncidentChannel
    priority: IncidentPriority

class CreateIncidentResponse(BaseModel):
    id: UUID
    message: str = "Incident created successfully"