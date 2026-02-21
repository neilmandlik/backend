from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from services.mock_fireflies import (
    get_transcript,
    get_transcripts_by_deal,
    get_transcripts_by_contact,
    get_transcripts_by_participant_email,
    get_transcripts,
)
from services.mock_hubspot import get_deal

router = APIRouter()


@router.get("/deal/{deal_id}")
def get_deal_transcripts(deal_id: str):
    """
    Get all Fireflies transcripts for a specific HubSpot deal.

    This mimics the flow:
    1. Get deal from HubSpot
    2. Get contacts associated with the deal
    3. Query Fireflies for transcripts with those participants
    """
    # Verify deal exists
    deal = get_deal(deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail=f"Deal {deal_id} not found")

    # Get transcripts for this deal
    transcripts = get_transcripts_by_deal(deal_id)

    return {
        "deal_id": deal_id,
        "deal_name": deal.name,
        "transcript_count": len(transcripts),
        "transcripts": [t.model_dump() for t in transcripts],
    }


@router.get("/{transcript_id}")
def get_transcript_detail(transcript_id: str):
    """Get full details of a specific transcript including sentences."""
    transcript = get_transcript(transcript_id)
    if not transcript:
        raise HTTPException(status_code=404, detail=f"Transcript {transcript_id} not found")

    return transcript.model_dump()


@router.get("")
def list_transcripts(
    participant_email: Optional[str] = None,
    contact_id: Optional[str] = None,
    limit: int = Query(50, le=200),
):
    """
    List transcripts with optional filtering.

    Query params:
    - participant_email: Filter by participant email (matches Fireflies API pattern)
    - contact_id: Filter by HubSpot contact ID
    - limit: Max results to return
    """
    if participant_email:
        transcripts = get_transcripts_by_participant_email(participant_email)
    elif contact_id:
        transcripts = get_transcripts_by_contact(contact_id)
    else:
        transcripts = get_transcripts()

    # Return condensed list format
    result = []
    for t in transcripts[:limit]:
        result.append({
            "id": t.id,
            "title": t.title,
            "date": t.date.isoformat(),
            "duration": t.duration,
            "participants": t.participants,
            "deal_id": t.deal_id,
            "transcript_url": t.transcript_url,
        })

    return {
        "total": len(transcripts),
        "count": len(result),
        "transcripts": result,
    }
