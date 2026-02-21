"""
Mock Fireflies transcript generator.
Generates realistic sales call transcripts for each deal with discoverable patterns.
"""

import random
from typing import List, Optional
from datetime import datetime, timedelta
from models.fireflies import (
    Transcript, TranscriptListItem, TranscriptSentence,
    TranscriptSummary, MeetingAttendee
)
from services.mock_hubspot import get_deals, get_contact, get_company

# Global data store
_transcripts: List[Transcript] = []
_generated = False

# Sales rep names (our team)
SALES_REPS = [
    ("Sarah", "Chen", "sarah.chen@imocha.io"),
    ("Rajesh", "Kumar", "rajesh.kumar@imocha.io"),
    ("Emily", "Johnson", "emily.johnson@imocha.io"),
    ("Amit", "Sharma", "amit.sharma@imocha.io"),
    ("Jennifer", "Taylor", "jennifer.taylor@imocha.io"),
]

# Call types and their characteristics
CALL_TEMPLATES = {
    "discovery": {
        "duration_range": (1800, 2700),  # 30-45 min
        "topics": ["Current hiring process", "Pain points", "Team size", "Budget timeline"],
        "action_items_won": [
            "Send product demo recording",
            "Schedule technical deep-dive with engineering team",
            "Share case study from similar company",
        ],
        "action_items_lost": [
            "Follow up next quarter",
            "Send comparison sheet",
            "Reconnect after budget review",
        ],
    },
    "demo": {
        "duration_range": (2400, 3600),  # 40-60 min
        "topics": ["Product walkthrough", "Integration capabilities", "Pricing discussion", "Implementation timeline"],
        "action_items_won": [
            "Prepare commercial proposal",
            "Schedule meeting with procurement",
            "Set up trial environment",
        ],
        "action_items_lost": [
            "Address integration concerns",
            "Provide ROI calculator",
            "Schedule follow-up in 2 weeks",
        ],
    },
    "negotiation": {
        "duration_range": (1500, 2400),  # 25-40 min
        "topics": ["Contract terms", "Pricing negotiation", "Implementation support", "Success metrics"],
        "action_items_won": [
            "Send final contract for signature",
            "Schedule kickoff call with CS team",
            "Confirm implementation start date",
        ],
        "action_items_lost": [
            "Revise proposal with adjusted pricing",
            "Escalate to VP Sales for approval",
            "Competitor comparison analysis",
        ],
    },
}

# Transcript content templates
OPENING_LINES = [
    "Thanks everyone for joining today's call.",
    "Good to see everyone here. Let's get started.",
    "Appreciate you taking the time to meet with us today.",
    "Thanks for making the time. I know everyone's schedule is packed.",
]

DISCOVERY_QUESTIONS = [
    "Can you walk me through your current hiring process?",
    "What are the biggest challenges you're facing with assessments today?",
    "How many candidates do you typically assess per month?",
    "What's your current tech stack for recruitment?",
    "Who else is involved in the evaluation process?",
]

OBJECTION_RESPONSES = {
    "Pricing per-candidate too high": [
        "I understand pricing is a concern. Let me show you the ROI data from similar customers.",
        "We can explore volume-based pricing tiers that might work better for your scale.",
    ],
    "Already using HackerRank/competitor": [
        "Many of our customers were using HackerRank before. The key differentiator is our AI proctoring.",
        "I'd love to show you a side-by-side comparison of what we offer versus your current tool.",
    ],
    "Need deeper ATS integration": [
        "We have native integrations with all major ATS platforms. Let me show you our integration roadmap.",
        "Our API is very flexible. We can work with your engineering team on custom integrations.",
    ],
    "Pricing too complex": [
        "Let me break down the pricing structure more clearly. We can simplify this.",
    ],
    "Integration gap with Workday/SAP": [
        "We actually just released our Workday connector last quarter. Let me walk you through it.",
    ],
}

POSITIVE_SIGNALS = [
    "This looks really interesting.",
    "I like what I'm seeing so far.",
    "This could definitely solve our problem.",
    "When could we get started?",
    "What's the typical implementation timeline?",
    "I want to bring my team in to see this.",
]

NEGATIVE_SIGNALS = [
    "We're already pretty invested in our current solution.",
    "The pricing is higher than we expected.",
    "We need to think about this more.",
    "I'm not sure this fits our budget right now.",
    "We have some concerns about the integration.",
    "Let me discuss this with my team and get back to you.",
]


def _generate_transcript_content(
    deal, contact, company, sales_rep_email: str, call_type: str, won: bool
) -> tuple:
    """Generate realistic transcript sentences and summary."""

    template = CALL_TEMPLATES[call_type]
    duration = random.randint(*template["duration_range"])

    # Generate sentences
    sentences = []
    current_time = 0.0

    # Opening
    rep_name = next(r for r in SALES_REPS if r[2] == sales_rep_email)
    rep_display = f"{rep_name[0]} {rep_name[1]}"
    prospect_display = f"{contact.first_name} {contact.last_name}"

    opening = random.choice(OPENING_LINES)
    sentence_duration = len(opening.split()) * 0.4
    sentences.append(TranscriptSentence(
        text=opening,
        speaker_name=rep_display,
        speaker_email=sales_rep_email,
        start_time=current_time,
        end_time=current_time + sentence_duration,
    ))
    current_time += sentence_duration + 1.5

    # Discovery/demo content
    if call_type == "discovery":
        for q in random.sample(DISCOVERY_QUESTIONS, 3):
            sentence_duration = len(q.split()) * 0.4
            sentences.append(TranscriptSentence(
                text=q,
                speaker_name=rep_display,
                speaker_email=sales_rep_email,
                start_time=current_time,
                end_time=current_time + sentence_duration,
            ))
            current_time += sentence_duration + 2.0

            # Prospect response
            response = f"Well, currently we're using a mix of tools and it's quite fragmented. We assess about {random.randint(50, 500)} candidates monthly."
            sentence_duration = len(response.split()) * 0.5
            sentences.append(TranscriptSentence(
                text=response,
                speaker_name=prospect_display,
                speaker_email=contact.email,
                start_time=current_time,
                end_time=current_time + sentence_duration,
            ))
            current_time += sentence_duration + 1.5

    # Objections (if any)
    if deal.objections:
        for objection in deal.objections[:2]:  # Include up to 2 objections
            # Prospect raises objection
            objection_text = f"One concern I have is: {objection.lower()}"
            sentence_duration = len(objection_text.split()) * 0.5
            sentences.append(TranscriptSentence(
                text=objection_text,
                speaker_name=prospect_display,
                speaker_email=contact.email,
                start_time=current_time,
                end_time=current_time + sentence_duration,
            ))
            current_time += sentence_duration + 2.0

            # Rep addresses objection
            if objection in OBJECTION_RESPONSES:
                response = random.choice(OBJECTION_RESPONSES[objection])
                sentence_duration = len(response.split()) * 0.4
                sentences.append(TranscriptSentence(
                    text=response,
                    speaker_name=rep_display,
                    speaker_email=sales_rep_email,
                    start_time=current_time,
                    end_time=current_time + sentence_duration,
                ))
                current_time += sentence_duration + 2.0

    # Closing signals
    if won:
        signal = random.choice(POSITIVE_SIGNALS)
    else:
        signal = random.choice(NEGATIVE_SIGNALS)

    sentence_duration = len(signal.split()) * 0.5
    sentences.append(TranscriptSentence(
        text=signal,
        speaker_name=prospect_display,
        speaker_email=contact.email,
        start_time=current_time,
        end_time=current_time + sentence_duration,
    ))
    current_time += sentence_duration + 2.0

    # Closing
    closing = "Thanks for your time today. I'll follow up with the next steps via email."
    sentence_duration = len(closing.split()) * 0.4
    sentences.append(TranscriptSentence(
        text=closing,
        speaker_name=rep_display,
        speaker_email=sales_rep_email,
        start_time=current_time,
        end_time=current_time + sentence_duration,
    ))

    # Generate summary
    action_items = template["action_items_won"] if won else template["action_items_lost"]
    keywords = [deal.product_line, company.industry, "Assessment", "Integration", "ROI"]
    if deal.competitor:
        keywords.append(deal.competitor)

    overview = f"{call_type.capitalize()} call with {company.name} regarding {deal.product_line}. "
    if won:
        overview += "Strong interest shown, moving forward with commercial proposal."
    else:
        overview += f"Some concerns raised about {deal.objections[0] if deal.objections else 'pricing'}. Following up next steps."

    summary = TranscriptSummary(
        overview=overview,
        action_items=random.sample(action_items, min(3, len(action_items))),
        keywords=keywords,
        topics_discussed=template["topics"],
    )

    return sentences, summary, duration


def generate_transcripts():
    """Generate 1-3 transcripts per deal (discovery, demo, negotiation calls)."""
    global _transcripts, _generated
    if _generated:
        return

    random.seed(42)
    deals = get_deals()
    transcript_id = 1

    for deal in deals:
        contact = get_contact(deal.contact_id)
        company = get_company(deal.company_id)
        if not contact or not company:
            continue

        # Assign a sales rep
        sales_rep = random.choice(SALES_REPS)
        sales_rep_email = sales_rep[2]

        won = deal.stage == "closedwon"

        # Won deals have 2-3 calls (discovery + demo + sometimes negotiation)
        # Lost deals have 1-2 calls (discovery + sometimes demo)
        if won:
            call_types = ["discovery", "demo"]
            if random.random() < 0.7:  # 70% have negotiation call
                call_types.append("negotiation")
        else:
            call_types = ["discovery"]
            if random.random() < 0.4:  # 40% get to demo
                call_types.append("demo")

        # Generate transcripts
        call_dates = []
        base_date = deal.create_date + timedelta(days=random.randint(3, 10))
        for i, call_type in enumerate(call_types):
            call_date = base_date + timedelta(days=i * random.randint(7, 14))
            call_dates.append(call_date)

        for i, call_type in enumerate(call_types):
            sentences, summary, duration = _generate_transcript_content(
                deal, contact, company, sales_rep_email, call_type, won
            )

            title = f"{company.name} - {call_type.capitalize()} Call"
            attendees = [
                MeetingAttendee(
                    display_name=f"{sales_rep[0]} {sales_rep[1]}",
                    email=sales_rep_email,
                ),
                MeetingAttendee(
                    display_name=f"{contact.first_name} {contact.last_name}",
                    email=contact.email,
                ),
            ]

            transcript = Transcript(
                id=f"transcript_{transcript_id:04d}",
                title=title,
                date=call_dates[i],
                duration=duration,
                host_email=sales_rep_email,
                organizer_email=sales_rep_email,
                participants=[sales_rep_email, contact.email],
                meeting_attendees=attendees,
                summary=summary,
                sentences=sentences,
                transcript_url=f"https://app.fireflies.ai/view/{transcript_id:04d}",
                deal_id=deal.id,
                contact_ids=[contact.id],
            )

            _transcripts.append(transcript)
            transcript_id += 1

    _generated = True


def get_transcripts() -> List[Transcript]:
    """Get all transcripts."""
    return _transcripts


def get_transcript(transcript_id: str) -> Optional[Transcript]:
    """Get a specific transcript by ID."""
    return next((t for t in _transcripts if t.id == transcript_id), None)


def get_transcripts_by_deal(deal_id: str) -> List[Transcript]:
    """Get all transcripts for a specific deal."""
    return [t for t in _transcripts if t.deal_id == deal_id]


def get_transcripts_by_contact(contact_id: str) -> List[Transcript]:
    """Get all transcripts involving a specific contact."""
    return [t for t in _transcripts if contact_id in t.contact_ids]


def get_transcripts_by_participant_email(email: str) -> List[Transcript]:
    """Get all transcripts with a specific participant email."""
    return [t for t in _transcripts if email.lower() in [p.lower() for p in t.participants]]
