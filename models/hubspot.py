from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class Company(BaseModel):
    id: str
    name: str
    industry: str
    employee_count: int
    annual_revenue: Optional[float] = None
    website: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None


class Contact(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    title: str
    seniority: str  # VP, Director, Manager, C-Level
    company_id: str


class Deal(BaseModel):
    id: str
    name: str
    stage: str  # "closedwon" or "closedlost"
    amount: float
    close_date: datetime
    create_date: datetime
    pipeline: str
    product_line: str  # "TA", "Skills Intelligence", "Full Platform"
    deal_source: str  # Referral, Inbound, Outbound, Partner, Event, G2
    loss_reason: Optional[str] = None
    competitor: Optional[str] = None
    company_id: str
    contact_id: str
    cycle_days: int
    objections: List[str] = []


class DealEnriched(Deal):
    company: Optional[Company] = None
    contact: Optional[Contact] = None
