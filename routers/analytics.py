from fastapi import APIRouter
from services.analytics import (
    compute_overview, compute_breakdown, compute_competitors,
    compute_objections, compute_icp,
)

router = APIRouter()


@router.get("/overview")
def overview():
    return compute_overview().model_dump()


@router.get("/breakdown/{dimension}")
def breakdown(dimension: str):
    """Dimensions: industry, deal_size, source, company_size, buyer_title"""
    valid = ["industry", "deal_size", "source", "company_size", "buyer_title"]
    if dimension not in valid:
        return {"error": f"Invalid dimension. Choose from: {valid}"}
    return [item.model_dump() for item in compute_breakdown(dimension)]


@router.get("/competitors")
def competitors():
    return [c.model_dump() for c in compute_competitors()]


@router.get("/objections")
def objections():
    return [o.model_dump() for o in compute_objections()]


@router.get("/icp")
def icp():
    return compute_icp().model_dump()
