from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# ── LEAD ──────────────────────────────────────
class LeadCreate(BaseModel):
    name: str
    budget: Optional[str] = None
    property_type: Optional[str] = None
    contact: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    property_title: Optional[str] = None
    property_price: Optional[str] = None
    property_location: Optional[str] = None
    status: Optional[str] = "warm"

class LeadResponse(BaseModel):
    id: int
    name: str
    phone: str
    email: str
    budget: Optional[str] = None
    property_type: Optional[str] = None
    property_title: Optional[str] = None
    property_price: Optional[str] = None
    property_location: Optional[str] = None

    class Config:
        from_attributes = True

# ── CAMPAIGN ───────────────────────────────────
class CampaignCreate(BaseModel):
    name: str
    description: str
    status: Optional[str] = "draft"

class CampaignResponse(BaseModel):
    id: int
    name: str
    description: str
    status: str
    lead_count: int
    created_at: datetime
    model_config = {"from_attributes": True}

# ── PROPERTY ───────────────────────────────────
class PropertyCreate(BaseModel):
    name: str
    address: str
    property_type: str
    price: float
    status: Optional[str] = "available"

class PropertyResponse(BaseModel):
    id: int
    name: str
    address: str
    property_type: str
    price: float
    status: str
    created_at: datetime
    model_config = {"from_attributes": True}

# ── AUTH ───────────────────────────────────────
class UserCreate(BaseModel):
    email: str
    name: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    model_config = {"from_attributes": True}

class Token(BaseModel):
    access_token: str
    token_type: str

# ── CHAT ───────────────────────────────────────
class ChatRequest(BaseModel):
    message: str