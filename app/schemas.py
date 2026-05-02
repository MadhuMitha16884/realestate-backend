from pydantic import BaseModel

class LeadCreate(BaseModel):
    name: str
    budget: str
    property_type: str
    contact: str

class ChatRequest(BaseModel):
    message: str