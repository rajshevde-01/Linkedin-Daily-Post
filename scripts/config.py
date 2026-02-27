"""
Configuration for Daily LinkedIn Post Automation
"""
import os
from datetime import datetime

# --- API Keys (from environment / GitHub Secrets) ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
LINKEDIN_ACCESS_TOKEN = os.environ.get("LINKEDIN_ACCESS_TOKEN", "")
LINKEDIN_PERSON_URN = os.environ.get("LINKEDIN_PERSON_URN", "")  # e.g., "urn:li:person:XXXX"

# --- Trusted RSS Feeds (tiered by reliability) ---
# Tier 1: Top-tier general tech news
# Tier 2: Reputable cybersecurity and developer news
# Tier 3: Focused blogs and communities
RSS_FEEDS = [
    # Tier 1 — Broad Tech News
    {"url": "https://www.wired.com/feed/rss", "name": "Wired", "tier": 1},
    {"url": "https://techcrunch.com/feed/", "name": "TechCrunch", "tier": 1},
    {"url": "https://www.theverge.com/rss/index.xml", "name": "The Verge", "tier": 1},

    # Tier 2 — Cyber & Developer News
    {"url": "https://feeds.feedburner.com/TheHackersNews", "name": "The Hacker News", "tier": 2},
    {"url": "https://www.bleepingcomputer.com/feed/", "name": "BleepingComputer", "tier": 2},
    {"url": "https://github.blog/feed/", "name": "GitHub Blog", "tier": 2},

    # Tier 3 — Expert Blogs & Deep Tech
    {"url": "https://krebsonsecurity.com/feed/", "name": "Krebs on Security", "tier": 3},
    {"url": "https://news.ycombinator.com/rss", "name": "Hacker News (YC)", "tier": 3},
]

# --- Day-of-Week Rotation ---
DAY_STYLES = {
    0: "Tech Leadership & Strategy",
    1: "AI & Future of Tech",
    2: "Cybersecurity Deep Dive",
    3: "Productivity & Developer Workflows",
    4: "Week in review — top tech news",
    5: "Soft Skills in Tech (Communication, Burnout)",
    6: "Coding / Open Source project highlights",
}

DAY_NAMES = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}

# --- Post Settings ---
POST_MIN_WORDS = 150
POST_MAX_WORDS = 220

# --- Hashtags (added automatically after generation) ---
HASHTAGS = [
    "#TechLeadership",
    "#Cybersecurity",
    "#OpenSource",
    "#SoftwareEngineering",
    "#FutureOfTech",
    "#DeveloperProductivity",
]


def get_today_style():
    """Return the post style for today based on day of week."""
    day = datetime.now().weekday()  # 0=Monday
    return DAY_STYLES[day], DAY_NAMES[day]


def get_system_prompt(news_context: str) -> str:
    """Build the full system prompt for post generation."""
    style, day_name = get_today_style()

    return f"""You are a Senior Technologist and Engineering Leader with 10+ years of experience in software development, cybersecurity, and tech leadership.

Your task is to write ONE LinkedIn post for today.

Today's date: {datetime.now().strftime('%B %d, %Y')}
Today is {day_name}, so the post style MUST be: {style}

Latest technology and industry news context:
{news_context}

STRICT RULES:
- Start with a powerful hook (shocking stat, bold question, or surprising fact)
- Length: {POST_MIN_WORDS}-{POST_MAX_WORDS} words only
- Tone: professional but human — like a real practitioner and leader, not a corporate bot
- Include ONE actionable tip or insight professionals can use TODAY
- End with an engaging question to spark comments
- NO hashtags (they are added automatically later)
- NO emojis in the body
- NO phrases like "In today's digital landscape" or "In conclusion"
- DO NOT mention AI or that this was generated
- Write in first person ("I", "we", "our team")

FACTUAL ACCURACY RULES (CRITICAL):
- ONLY reference news stories, projects, or incidents that are listed in the VERIFIED NEWS section above
- DO NOT invent statistics, company names, or incident details
- If you cite a number or percentage, it must come directly from the provided news context
- If the news context is insufficient or irrelevant to today's theme, write the post based on general well-known tech principles, open-source knowledge, and your practitioner experience — do NOT fabricate specific events
- When in doubt, be general and insightful rather than specific and fabricated.

Output ONLY the post text. Nothing else. No labels, no preamble."""

