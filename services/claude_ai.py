"""Claude AI service with 7 prompt templates and response caching."""

import json
import os
import sys
from typing import Dict, Optional
import anthropic

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from services.analytics import (
    compute_overview, compute_breakdown, compute_competitors,
    compute_objections, compute_icp,
)
from services.mock_hubspot import get_deals, get_companies

# Response cache
_cache: Dict[str, str] = {}

SYSTEM_PROMPT = """You are an expert B2B sales analyst and strategy consultant. You analyze CRM deal data to find patterns, generate insights, and provide actionable recommendations.

Rules:
- Be specific and data-driven. Reference actual numbers from the data.
- Use markdown formatting for readability.
- Keep responses concise but comprehensive.
- Focus on actionable insights, not just observations.
- When recommending actions, be specific about what to do differently.
"""


def _get_data_context() -> str:
    """Build a data summary string for the AI prompts."""
    overview = compute_overview()
    industry_breakdown = compute_breakdown("industry")
    size_breakdown = compute_breakdown("deal_size")
    source_breakdown = compute_breakdown("source")
    company_size = compute_breakdown("company_size")
    buyer_breakdown = compute_breakdown("buyer_title")
    competitors = compute_competitors()
    objections = compute_objections()
    icp = compute_icp()

    return f"""
## Dataset Summary
- Total deals: {overview.total_deals} | Won: {overview.won_deals} | Lost: {overview.lost_deals}
- Overall win rate: {overview.win_rate}%
- Total revenue (won): ${overview.total_revenue:,.0f}
- Avg deal size (won): ${overview.avg_deal_size:,.0f}
- Avg cycle (won): {overview.avg_cycle_won} days | Avg cycle (lost): {overview.avg_cycle_lost} days

## Win Rate by Industry
{chr(10).join(f"- {b.category}: {b.win_rate}% ({b.won}/{b.total} deals, ${b.total_revenue:,.0f} revenue)" for b in industry_breakdown)}

## Win Rate by Deal Size
{chr(10).join(f"- {b.category}: {b.win_rate}% ({b.won}/{b.total} deals)" for b in size_breakdown)}

## Win Rate by Source
{chr(10).join(f"- {b.category}: {b.win_rate}% ({b.won}/{b.total} deals)" for b in source_breakdown)}

## Win Rate by Company Size
{chr(10).join(f"- {b.category}: {b.win_rate}% ({b.won}/{b.total} deals)" for b in company_size)}

## Win Rate by Buyer Seniority
{chr(10).join(f"- {b.category}: {b.win_rate}% ({b.won}/{b.total} deals)" for b in buyer_breakdown)}

## Competitor Analysis
{chr(10).join(f"- {c.competitor}: {c.win_rate}% win rate ({c.wins}/{c.deals_faced} deals), top loss reasons: {', '.join(c.top_loss_reasons)}" for c in competitors)}

## Top Objections
{chr(10).join(f"- {o.objection}: raised {o.frequency} times, {o.win_rate_when_raised}% win rate when raised, industries: {', '.join(o.industries)}" for o in objections)}

## Current ICP
- Industries: {', '.join(icp.industries)}
- Company size: {icp.employee_range}
- Deal size: {icp.deal_size_range}
- Buyer titles: {', '.join(icp.buyer_titles)}
- Top sources: {', '.join(icp.preferred_sources)}
"""


PROMPT_TEMPLATES = {
    "win_loss_summary": """Based on the following CRM deal data, provide an executive summary of win/loss patterns.

{data}

Provide:
1. **Key Headline** — one sentence capturing the biggest insight
2. **Top 3 Win Patterns** — what correlates most with winning
3. **Top 3 Loss Patterns** — what correlates most with losing
4. **Revenue Impact** — quantify what improving the weakest area could mean
5. **Immediate Actions** — 3 specific things the sales team should do this quarter
""",

    "icp_generation": """Based on the following CRM deal data, generate a detailed Ideal Customer Profile.

{data}

Provide:
1. **Ideal Customer Profile** — specific firmographic criteria with confidence levels
2. **Why These Criteria** — data backing for each criterion
3. **Disqualification Criteria** — red flags that indicate low win probability
4. **Scoring Model** — how to score new leads (High/Medium/Low fit)
5. **Positioning by Segment** — how to tailor messaging for the ideal profile
""",

    "competitor_briefing": """Based on the following CRM deal data, create a competitive intelligence briefing.

{data}

For each competitor, provide:
1. **Threat Level** — High/Medium/Low with reasoning
2. **Where They Win** — industries, deal sizes, scenarios where we lose to them
3. **Where We Win** — our advantages against this competitor
4. **Battle Card Points** — 3-4 key talking points for sales reps
5. **Recommended Strategy** — how to approach deals where this competitor is present
""",

    "positioning": """Based on the following CRM deal data, recommend positioning improvements.

{data}

Provide:
1. **Current Positioning Assessment** — what our win patterns say about our perceived value
2. **Messaging Recommendations** — specific messaging changes by segment
3. **Proof Points to Develop** — case studies and data points we should collect
4. **Pricing Strategy** — observations about our pricing sweet spot and recommendations
5. **Channel Strategy** — which channels to invest in based on win rates
""",

    "industry_loss": """Based on the following CRM deal data, analyze why we lose in {industry}.

{data}

Provide:
1. **Root Cause Analysis** — the top 3 reasons we lose in this industry
2. **Comparison** — how this industry differs from our best-performing industries
3. **Competitor Factor** — which competitors are strongest in this industry
4. **Turnaround Strategy** — specific steps to improve win rates in this industry
5. **Go/No-Go Criteria** — when to pursue vs. walk away from deals in this industry
""",

    "sales_scripts": """Based on the following CRM deal data, create objection handling guidance.

{data}

For the top objections, provide:
1. **Objection Response Scripts** — specific language to address each objection
2. **Discovery Questions** — questions to ask early to surface and prevent objections
3. **Qualification Framework** — questions to determine if a deal is worth pursuing
4. **Email Templates** — follow-up email language for common objection scenarios
5. **Escalation Triggers** — when to bring in leadership or technical resources
""",

    "ask_ai": """You are a sales intelligence assistant. Answer the following question using only the provided CRM deal data. Be specific, cite numbers, and give actionable advice.

{data}

Question: {question}

Provide a clear, data-backed answer. If the question can't be answered from the data, say so.
""",
}


async def generate_insight(prompt_type: str, industry: Optional[str] = None,
                           question: Optional[str] = None) -> str:
    """Generate AI insight using Claude API with caching."""
    cache_key = f"{prompt_type}:{industry or ''}:{question or ''}"
    if cache_key in _cache:
        return _cache[cache_key]

    if not ANTHROPIC_API_KEY:
        # Return a mock response for demo without API key
        return _generate_mock_response(prompt_type, industry, question)

    template = PROMPT_TEMPLATES.get(prompt_type)
    if not template:
        return "Unknown prompt type."

    data_context = _get_data_context()
    prompt = template.format(data=data_context, industry=industry or "", question=question or "")

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        result = message.content[0].text
        _cache[cache_key] = result
        return result
    except Exception as e:
        return f"AI analysis unavailable: {str(e)}"


def _generate_mock_response(prompt_type: str, industry: Optional[str] = None,
                            question: Optional[str] = None) -> str:
    """Generate realistic mock AI responses when no API key is configured."""
    overview = compute_overview()
    industry_bd = compute_breakdown("industry")
    competitors = compute_competitors()

    top_industry = max(industry_bd, key=lambda x: x.win_rate)
    worst_industry = min(industry_bd, key=lambda x: x.win_rate)
    worst_competitor = min(competitors, key=lambda x: x.win_rate) if competitors else None

    mock_responses = {
        "win_loss_summary": f"""## Executive Win/Loss Summary

### Key Headline
**Our sweet spot is mid-market Technology and Healthcare companies in the $25K-$75K deal range, but we're hemorrhaging revenue in enterprise deals above $150K.**

### Top 3 Win Patterns
1. **Industry Fit**: {top_industry.category} leads with a {top_industry.win_rate}% win rate ({top_industry.won} wins from {top_industry.total} deals), generating ${top_industry.total_revenue:,.0f} in revenue
2. **Deal Size Sweet Spot**: Deals between $25K-$75K close at 62%+ — our product-market fit is strongest here
3. **Referral Channel**: Referral-sourced deals win at 70%, nearly 2.5x our outbound rate of 30%

### Top 3 Loss Patterns
1. **Large Enterprise Deals**: Deals over $150K win at only ~23% — we lack enterprise readiness
2. **{worst_industry.category} Industry**: Only {worst_industry.win_rate}% win rate across {worst_industry.total} deals — poor product-market fit
3. **Outbound-Sourced Deals**: 30% win rate suggests targeting and/or messaging problems

### Revenue Impact
Improving {worst_industry.category} win rate from {worst_industry.win_rate}% to 40% could generate an estimated additional $180K annually. Improving outbound conversion from 30% to 40% could add another $250K.

### Immediate Actions
1. **Deprioritize large enterprise deals** (>$150K) until product has enterprise features; focus reps on $25K-$75K range
2. **Double down on referral program** — invest in customer advocacy and referral incentives
3. **Retrain outbound team** on new ICP targeting criteria focusing on Technology and Healthcare companies with 50-500 employees""",

        "icp_generation": f"""## Ideal Customer Profile

### Primary ICP (High Confidence: 82%)

| Criterion | Ideal Profile | Confidence |
|-----------|--------------|------------|
| **Industry** | Technology, Healthcare | High (90%) |
| **Company Size** | 50-500 employees | High (88%) |
| **Deal Size** | $25,000 - $75,000 | High (85%) |
| **Buyer Title** | VP, Director, C-Level | Medium (78%) |
| **Lead Source** | Referral, Partner | High (85%) |

### Why These Criteria
- **Technology** wins at {top_industry.win_rate}% vs overall {overview.win_rate}% — our product resonates most with tech-forward buyers
- **50-500 employees** = right complexity level; large enough to have budget, small enough to make fast decisions
- **$25K-$75K** = our proven value delivery zone; above this, we compete with enterprise vendors

### Disqualification Criteria (Walk Away)
- Manufacturing or Retail with 1000+ employees (sub-30% win rate)
- Deals over $150K without executive sponsor at VP+ level
- Outbound-sourced deal with Manager-level contact only
- Competitor is {worst_competitor.competitor if worst_competitor else 'ZetaFlow'} AND deal is in their stronghold industry

### Lead Scoring Model
- **A-Lead (80%+ expected win rate)**: Tech/Healthcare + 50-500 emp + Referral + VP/Director buyer
- **B-Lead (50-80%)**: Right industry OR right size + decent source
- **C-Lead (30-50%)**: Mixed signals, one strong factor
- **D-Lead (<30%)**: Multiple red flags, deprioritize

### Positioning by Segment
- **Tech companies**: Lead with innovation speed, API-first architecture, developer experience
- **Healthcare**: Lead with compliance, security, and patient data handling
- **Mid-market**: Emphasize rapid time-to-value and dedicated support""",

        "competitor_briefing": f"""## Competitive Intelligence Briefing

{chr(10).join(f'''### {c.competitor}
- **Threat Level**: {"HIGH" if c.win_rate < 35 else "MEDIUM" if c.win_rate < 50 else "LOW"} — {c.win_rate}% win rate when they're involved ({c.losses} losses to them)
- **Where They Win**: {', '.join(c.industries[:2])} — particularly in deals where {c.top_loss_reasons[0] if c.top_loss_reasons else "price"} is the deciding factor
- **Where We Win**: Deals with VP+ buyers and referral sources; our relationship-based selling outperforms their product-led approach
- **Battle Card**:
  1. Ask about their experience with {c.competitor}'s implementation timeline (typically 2-3x longer)
  2. Reference our {c.industries[0] if c.industries else "industry"}-specific case studies
  3. Offer a technical proof-of-concept to demonstrate superiority in their specific use case
  4. Highlight our customer retention rate and dedicated support model
''' for c in competitors[:4])}""",

        "positioning": f"""## Positioning Recommendations

### Current Positioning Assessment
Our win patterns reveal we're positioned as a **mid-market solution for technology-forward companies**. Our sweet spot ($25K-$75K) suggests buyers see us as a professional-tier tool, not an enterprise platform.

### Messaging Recommendations
1. **For Technology**: Emphasize speed, API flexibility, and developer experience. Win rate: {top_industry.win_rate}%
2. **For Healthcare**: Lead with compliance, HIPAA readiness, and data security. Tailor demos to health-specific workflows
3. **For all segments**: Shift from feature-based to outcome-based messaging. Quantify ROI in terms they care about

### Proof Points to Develop
- ROI case study from a 200-employee Technology company (our ideal win scenario)
- Security audit / compliance certification for Healthcare segment
- Implementation speed benchmark (target: <30 days to value)

### Pricing Strategy
- **Sweet spot is $25K-$75K** — hold firm in this range, don't discount
- **Above $75K**: Bundle additional services to justify, or restructure as phased engagement
- **Above $150K**: Only pursue with executive sponsorship and multi-year commitment

### Channel Strategy
- **Invest heavily in Referral** (70% win rate) — launch formal referral program
- **Improve Inbound** (48% win rate) — optimize qualification to filter out poor-fit leads
- **Reduce Outbound spend** (30% win rate) — unless retargeted at ICP criteria""",

        "industry_loss": f"""## Why We Lose in {industry or worst_industry.category}

### Root Cause Analysis
1. **Product-Market Misfit**: {industry or worst_industry.category} companies typically have complex legacy systems that our integration layer doesn't handle well
2. **Wrong Buyer Level**: We're engaging too many Manager-level contacts (30% win rate) instead of VPs/Directors who can champion internally
3. **Competitive Disadvantage**: Specialized {industry or worst_industry.category} vendors have deeper domain expertise and established relationships

### Comparison with Best Industries
| Factor | Technology ({top_industry.win_rate}% win) | {industry or worst_industry.category} ({worst_industry.win_rate}% win) |
|--------|------------|---------------|
| Typical company size | 100-300 emp | 1000+ emp |
| Decision maker | VP/CTO | IT Manager |
| Sales cycle | ~30 days | ~70 days |
| Main objection | Feature questions | Price + Integration |

### Turnaround Strategy
1. **Narrow targeting**: Only pursue {industry or worst_industry.category} companies with <500 employees
2. **Build 2-3 {industry or worst_industry.category} case studies** to establish credibility
3. **Partner with a {industry or worst_industry.category} consultant** for co-selling
4. **Develop industry-specific demo** showcasing relevant use cases

### Go/No-Go Criteria
**Pursue if**: <500 employees, VP+ buyer, referral source, no ZetaFlow competitor, budget confirmed
**Walk away if**: 1000+ employees, Manager contact only, outbound source, 3+ competitors involved""",

        "sales_scripts": f"""## Objection Handling Guide

### Top Objections & Response Scripts

**1. "Price too high"** (Most frequent)
> "I understand budget is a key consideration. Let me ask — what would the cost of *not* solving this problem be over the next 12 months? Our customers in similar situations typically see ROI within 90 days. Let me walk you through a specific example..."

**Discovery question**: "What's your current budget range for this initiative, and how was it determined?"

**2. "Missing integration"**
> "That's great feedback. Which specific integrations are must-haves for your workflow? We've found that 80% of our customers need [X, Y, Z] — and we have those covered. For anything custom, our API allows you to build exactly what you need in days, not months."

**Discovery question**: "Can you walk me through your current tech stack and the data flows between systems?"

**3. "Security concerns"**
> "Security is something we take extremely seriously — it's actually one of our strongest differentiators. We're SOC 2 Type II certified, and I can connect you with our security team for a deep-dive. Would it help if I shared our security whitepaper and audit reports?"

**Discovery question**: "What are your organization's specific security requirements and compliance frameworks?"

### Qualification Framework (BANT+)
1. **Budget**: Is there allocated budget, or is this exploratory?
2. **Authority**: Is our contact the decision maker, or do we need executive access?
3. **Need**: Is this solving an active pain point or a nice-to-have?
4. **Timeline**: Is there a compelling event driving the decision?
5. **Fit**: Does this company match our ICP criteria?

### Escalation Triggers
- Bring in **Sales Engineering** when: technical objections arise in first 2 calls
- Bring in **VP of Sales** when: deal >$75K and competitor is ZetaFlow
- Bring in **Customer Success** when: prospect asks about implementation and support""",

        "ask_ai": f"""Based on the CRM data analysis:

**Overall Performance**: {overview.total_deals} total deals with a {overview.win_rate}% win rate, generating ${overview.total_revenue:,.0f} in revenue from {overview.won_deals} won deals.

**Key Finding**: The data shows a strong correlation between company size (50-500 employees), deal size ($25K-$75K), and win rates. Technology and Healthcare industries are our strongest segments.

**Recommendation**: Focus sales efforts on mid-market Technology and Healthcare companies, leverage referral channels, and engage VP+ level decision makers for optimal win rates.

To answer your specific question: {question or 'Please ask a specific question about the deal data.'}""",
    }

    return mock_responses.get(prompt_type, "Analysis not available for this prompt type.")
