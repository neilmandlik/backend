from pydantic import BaseModel
from typing import List, Optional


class OverviewMetrics(BaseModel):
    total_deals: int
    won_deals: int
    lost_deals: int
    win_rate: float
    total_revenue: float
    avg_deal_size: float
    avg_cycle_won: float
    avg_cycle_lost: float


class BreakdownItem(BaseModel):
    category: str
    total: int
    won: int
    lost: int
    win_rate: float
    avg_deal_size: float
    total_revenue: float


class CompetitorMetrics(BaseModel):
    competitor: str
    deals_faced: int
    wins: int
    losses: int
    win_rate: float
    avg_deal_size: float
    top_loss_reasons: List[str]
    industries: List[str]


class ObjectionTheme(BaseModel):
    objection: str
    frequency: int
    percentage: float
    industries: List[str]
    win_rate_when_raised: float


class ICPProfile(BaseModel):
    industries: List[str]
    employee_range: str
    deal_size_range: str
    buyer_titles: List[str]
    preferred_sources: List[str]
    avg_cycle_days: int
    win_rate: float
    confidence: float


class AIInsightResponse(BaseModel):
    content: str
    prompt_type: str
    cached: bool = False


class AskAIRequest(BaseModel):
    question: str


class AskAIResponse(BaseModel):
    answer: str
    question: str
