from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models, schemas
from app.database import get_db
from groq import Groq
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
import os
from twilio.rest import Client as TwilioClient

# Twilio setup — reads from .env
twilio_client = TwilioClient(
    os.getenv("TWILIO_ACCOUNT_SID"),
    os.getenv("TWILIO_AUTH_TOKEN")
)
TWILIO_FROM        = os.getenv("TWILIO_FROM_NUMBER")
AGENT_PHONE        = os.getenv("AGENT_PHONE_NUMBER")
WHATSAPP_FROM      = os.getenv("TWILIO_WHATSAPP_FROM")  # whatsapp:+14155238886

router = APIRouter()

# ── AUTH SETUP ─────────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str):
    return pwd_context.verify(plain, hashed)

def create_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def send_sms_to_agent(lead_name: str, lead_phone: str, lead_email: str):
    """Sends SMS alert to agent when a new lead is created."""
    try:
        message = twilio_client.messages.create(
            body=(
                f"🏠 New Lead Alert!\n"
                f"Name:  {lead_name}\n"
                f"Phone: {lead_phone}\n"
                f"Email: {lead_email}\n"
                f"Login to your dashboard to follow up."
            ),
            from_=TWILIO_FROM,
            to=AGENT_PHONE
        )
        print(f"SMS sent to agent. SID: {message.sid}")
        return True
    except Exception as e:
        print(f"SMS failed: {e}")
        return False


def send_whatsapp_to_lead(lead_phone: str, lead_name: str, property_title: str,
                           property_price: str, property_location: str):
    """Sends WhatsApp message to lead with property details."""
    try:
        # Lead phone must be in format: whatsapp:+91xxxxxxxxxx
        to_whatsapp = f"whatsapp:{lead_phone}"
        
        message = twilio_client.messages.create(
            body=(
                f"Hello {lead_name}! 👋\n\n"
                f"Thank you for your interest. Here are the property details:\n\n"
                f"🏡 *{property_title}*\n"
                f"📍 Location: {property_location}\n"
                f"💰 Price: {property_price}\n\n"
                f"Our agent will contact you shortly. "
                f"Reply to this message with any questions!"
            ),
            from_=WHATSAPP_FROM,
            to=to_whatsapp
        )
        print(f"WhatsApp sent to lead. SID: {message.sid}")
        return True
    except Exception as e:
        print(f"WhatsApp failed: {e}")
        return False


# ── AUTH ROUTES ────────────────────────────────────────────────────────────────
@router.post("/auth/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    db_user = models.User(
        email=user.email,
        name=user.name,
        hashed_password=hash_password(user.password)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/auth/login", response_model=schemas.Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Wrong email or password")
    token = create_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}

# ── LEAD ROUTES ────────────────────────────────────────────────────────────────
@router.post("/lead", response_model=dict)
async def create_lead(lead: schemas.LeadCreate, db: Session = Depends(get_db)):
    db_lead = models.Lead(
        name=lead.name,
        budget=lead.budget,
        property_type=lead.property_type,
        contact=lead.phone or lead.contact or "",
        status=lead.status or "warm"
    )
    db.add(db_lead)
    db.commit()
    db.refresh(db_lead)

    # ✅ NEW: Send SMS to agent
    send_sms_to_agent(
        lead_name=lead.name,
        lead_phone=lead.phone or lead.contact or "",
        lead_email=lead.email or ""
    )

    # ✅ NEW: Send WhatsApp to lead with property info
    if (lead.phone or lead.contact) and getattr(lead, "property_title", None):
        send_whatsapp_to_lead(
            lead_phone=lead.phone or lead.contact,
            lead_name=lead.name,
            property_title=lead.property_title,
            property_price=lead.property_price or "Contact us",
            property_location=lead.property_location or "See listing"
        )

    return {"message": "Lead created successfully", "lead_id": db_lead.id}

@router.get("/leads", response_model=list[schemas.LeadResponse])
def get_leads(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return db.query(models.Lead).offset(skip).limit(limit).all()

@router.get("/leads/{lead_id}", response_model=schemas.LeadResponse)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

@router.delete("/leads/{lead_id}")
def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    db.delete(lead)
    db.commit()
    return {"message": "Lead deleted"}

# ── DASHBOARD ROUTE ────────────────────────────────────────────────────────────
@router.get("/dashboard/stats")
def get_stats(db: Session = Depends(get_db)):
    total_leads = db.query(func.count(models.Lead.id)).scalar()
    hot_leads = db.query(func.count(models.Lead.id)).filter(models.Lead.status == "hot").scalar()
    warm_leads = db.query(func.count(models.Lead.id)).filter(models.Lead.status == "warm").scalar()
    cold_leads = db.query(func.count(models.Lead.id)).filter(models.Lead.status == "cold").scalar()
    total_campaigns = db.query(func.count(models.Campaign.id)).scalar()
    total_properties = db.query(func.count(models.Property.id)).scalar()
    return {
        "total_leads": total_leads,
        "hot_leads": hot_leads,
        "warm_leads": warm_leads,
        "cold_leads": cold_leads,
        "total_campaigns": total_campaigns,
        "total_properties": total_properties
    }

# ── CAMPAIGN ROUTES ────────────────────────────────────────────────────────────
@router.post("/campaigns", response_model=schemas.CampaignResponse)
def create_campaign(campaign: schemas.CampaignCreate, db: Session = Depends(get_db)):
    db_campaign = models.Campaign(**campaign.model_dump())
    db.add(db_campaign)
    db.commit()
    db.refresh(db_campaign)
    return db_campaign

@router.get("/campaigns", response_model=list[schemas.CampaignResponse])
def get_campaigns(db: Session = Depends(get_db)):
    return db.query(models.Campaign).all()

@router.delete("/campaigns/{campaign_id}")
def delete_campaign(campaign_id: int, db: Session = Depends(get_db)):
    campaign = db.query(models.Campaign).filter(models.Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    db.delete(campaign)
    db.commit()
    return {"message": "Campaign deleted"}

# ── PROPERTY ROUTES ────────────────────────────────────────────────────────────
@router.post("/properties", response_model=schemas.PropertyResponse)
def create_property(prop: schemas.PropertyCreate, db: Session = Depends(get_db)):
    db_prop = models.Property(**prop.model_dump())
    db.add(db_prop)
    db.commit()
    db.refresh(db_prop)
    return db_prop

@router.get("/properties", response_model=list[schemas.PropertyResponse])
def get_properties(db: Session = Depends(get_db)):
    return db.query(models.Property).all()

# ── CHAT ROUTE ─────────────────────────────────────────────────────────────────
@router.post("/chat")
def chat(request: schemas.ChatRequest):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a helpful real estate assistant in India. Suggest properties based on user needs. Be specific about locations, prices and property types."},
            {"role": "user", "content": request.message}
        ]
    )
    return {"response": response.choices[0].message.content}

# ── HEALTH CHECK ───────────────────────────────────────────────────────────────
@router.get("/health")
def health():
    return {"status": "healthy", "message": "Backend is running!"}

@router.post("/ai/score-lead")
def score_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    prompt = f"""
    Score this real estate lead from 0 to 100 based on buying potential.
    Name: {lead.name}
    Budget: {lead.budget}
    Property Type: {lead.property_type}
    Intent: {lead.intent}
    Current Status: {lead.status}
    Rules:
    - Higher budget = higher score
    - Hot status = higher score
    - Buy/Invest intent = higher score
    - Rent intent = lower score
    Reply with ONLY a number between 0 and 100. Nothing else.
    """
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a real estate lead scoring expert. Reply only with a number."},
            {"role": "user", "content": prompt}
        ]
    )
    try:
        score = int(response.choices[0].message.content.strip())
        score = max(0, min(100, score))
    except:
        score = 50
    lead.score = score
    db.commit()
    return {"lead_id": lead_id, "name": lead.name, "score": score, "message": f"Lead scored {score}/100"}


@router.post("/ai/match-property")
def match_property(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    properties = db.query(models.Property).filter(models.Property.status == "available").all()
    if not properties:
        return {"message": "No properties available for matching"}
    props_text = "\n".join([
        f"ID:{p.id} Name:{p.name} Type:{p.property_type} Price:₹{p.price} Location:{p.address}"
        for p in properties
    ])
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    prompt = f"""
    Match this lead to the best property from the list below.
    Lead:
    - Budget: {lead.budget}
    - Property Type: {lead.property_type}
    - Intent: {lead.intent}
    Available Properties:
    {props_text}
    Reply with ONLY the property ID number that best matches. Nothing else.
    """
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a real estate matching expert. Reply only with a property ID number."},
            {"role": "user", "content": prompt}
        ]
    )
    try:
        matched_id = int(response.choices[0].message.content.strip())
        matched = db.query(models.Property).filter(models.Property.id == matched_id).first()
    except:
        matched = properties[0]
    if matched:
        match = models.LeadPropertyMatch(
            lead_id=lead_id,
            property_id=matched.id,
            match_score=0.95
        )
        db.add(match)
        db.commit()
    return {
        "lead_id": lead_id,
        "lead_name": lead.name,
        "matched_property": matched.name if matched else "None",
        "property_address": matched.address if matched else "None",
        "property_price": matched.price if matched else 0,
        "message": "Best property matched by AI!"
    }


@router.get("/analytics/leads-by-day")
def leads_by_day(db: Session = Depends(get_db)):
    from sqlalchemy import cast, Date
    results = db.query(
        cast(models.Lead.created_at, Date).label("date"),
        func.count(models.Lead.id).label("count")
    ).group_by(cast(models.Lead.created_at, Date)).order_by("date").all()
    return [{"date": str(r.date), "count": r.count} for r in results]


@router.get("/analytics/funnel")
def conversion_funnel(db: Session = Depends(get_db)):
    total = db.query(func.count(models.Lead.id)).scalar()
    hot = db.query(func.count(models.Lead.id)).filter(models.Lead.status == "hot").scalar()
    warm = db.query(func.count(models.Lead.id)).filter(models.Lead.status == "warm").scalar()
    cold = db.query(func.count(models.Lead.id)).filter(models.Lead.status == "cold").scalar()
    return {
        "total_leads": total,
        "warm_leads": warm,
        "hot_leads": hot,
        "cold_leads": cold,
        "conversion_rate": f"{round((hot / total * 100), 1) if total > 0 else 0}%"
    }


@router.get("/analytics/budget-distribution")
def budget_distribution(db: Session = Depends(get_db)):
    leads = db.query(models.Lead).all()
    distribution = {"Under 30L": 0, "30L-50L": 0, "50L-1Cr": 0, "Above 1Cr": 0}
    for lead in leads:
        budget = lead.budget.lower().replace(" ", "")
        if "cr" in budget or "crore" in budget:
            distribution["Above 1Cr"] += 1
        elif any(x in budget for x in ["50l", "60l", "70l", "80l", "90l"]):
            distribution["50L-1Cr"] += 1
        elif any(x in budget for x in ["30l", "35l", "40l", "45l"]):
            distribution["30L-50L"] += 1
        else:
            distribution["Under 30L"] += 1
    return distribution