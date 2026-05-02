from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from groq import Groq
import os

router = APIRouter()

@router.post("/lead")
def create_lead(lead: schemas.LeadCreate, db: Session = Depends(get_db)):
    db_lead = models.Lead(
        name=lead.name,
        budget=lead.budget,
        property_type=lead.property_type,
        contact=lead.contact
    )
    db.add(db_lead)
    db.commit()
    db.refresh(db_lead)
    return {"message": "Lead saved successfully!", "id": db_lead.id}

@router.post("/chat")
def chat(request: schemas.ChatRequest):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a helpful real estate assistant in India. Suggest properties based on user needs."},
            {"role": "user", "content": request.message}
        ]
    )
    return {"response": response.choices[0].message.content}