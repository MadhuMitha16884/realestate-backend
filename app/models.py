from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean
from sqlalchemy.sql import func
from app.database import Base

class Lead(Base):
    __tablename__ = "leads"
    id               = Column(Integer, primary_key=True, index=True)
    name             = Column(String)
    budget           = Column(String)
    property_type    = Column(String)
    contact          = Column(String)
    phone            = Column(String)            # ✅ NEW
    email            = Column(String)            # ✅ NEW
    property_title   = Column(String)            # ✅ NEW
    property_price   = Column(String)            # ✅ NEW
    property_location = Column(String)           # ✅ NEW
    status           = Column(String, default="warm")
    score            = Column(Integer, default=0)
    intent           = Column(String, default="Buy")
    created_at       = Column(DateTime, default=func.now())

class Campaign(Base):
    __tablename__ = "campaigns"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(String)
    status = Column(String, default="draft")
    lead_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())

class Property(Base):
    __tablename__ = "properties"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    address = Column(String)
    property_type = Column(String)
    price = Column(Float)
    status = Column(String, default="available")
    created_at = Column(DateTime, default=func.now())

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    phone = Column(String, nullable=True)
    company = Column(String, nullable=True)
    role = Column(String, default="agent")
    created_at = Column(DateTime, default=func.now())

class LeadPropertyMatch(Base):
    __tablename__ = "lead_property_matches"
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer)
    property_id = Column(Integer)
    match_score = Column(Float)
    created_at = Column(DateTime, default=func.now()) 

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, nullable=False)
    role = Column(String, nullable=False)
    content = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())    
