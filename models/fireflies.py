from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class TranscriptSentence(BaseModel):
    """Individual line in a transcript with speaker and timing."""
    text: str
    speaker_name: str
    speaker_email: Optional[str] = None
    start_time: float  # seconds from start
    end_time: float


class TranscriptSummary(BaseModel):
    """AI-generated summary from Fireflies."""
    overview: str
    action_items: List[str]
    keywords: List[str]
    topics_discussed: List[str]


class MeetingAttendee(BaseModel):
    """Participant in the call."""
    display_name: str
    email: str
    phone_number: Optional[str] = None


class Transcript(BaseModel):
    """Full Fireflies transcript data."""
    id: str
    title: str
    date: datetime
    duration: int  # seconds
    host_email: str
    organizer_email: str
    participants: List[str]  # list of emails
    meeting_attendees: List[MeetingAttendee]
    summary: TranscriptSummary
    sentences: List[TranscriptSentence]
    audio_url: Optional[str] = None
    video_url: Optional[str] = None
    transcript_url: str
    # Link to HubSpot
    deal_id: Optional[str] = None
    contact_ids: List[str] = []


class TranscriptListItem(BaseModel):
    """Condensed transcript info for listing."""
    id: str
    title: str
    date: datetime
    duration: int
    participants: List[str]
    deal_id: Optional[str] = None
