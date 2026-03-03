"""
Configuration for Daily LinkedIn Post Automation
"""
import os
import random
from datetime import datetime

# --- API Keys (from environment / GitHub Secrets) ---
GROQ_API_KEY_ENV = os.environ.get("GROQ_API_KEY", "")
# Parse into a list of keys, splitting by comma and stripping whitespace
GROQ_API_KEYS = [k.strip() for k in GROQ_API_KEY_ENV.split(",") if k.strip()]
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
POST_MAX_WORDS = 280  # Increased to allow for polls and links

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
    """Return a random post style for this generation."""
    day = datetime.now().weekday()  # 0=Monday
    day_name = DAY_NAMES[day]
    style = random.choice(list(DAY_STYLES.values()))
    return style, day_name


def get_system_prompt(content: str, is_custom: bool = False, is_cve: bool = False, is_knowledge: bool = False) -> str:
    """Build the full system prompt for post generation."""
    style, day_name = get_today_style()
    
    if is_cve:
        context_label = "Live Zero-Day / CVE Threat Intelligence:"
        persona = "You are a hardcore Incident Responder and Threat Hunter."
    elif is_knowledge:
        context_label = "Personal Brain Note / Code / Architecture Snippet:"
        persona = "You are a Senior Technologist and Engineering Leader sharing a genuine insight directly derived from your personal work/notes."
    elif is_custom:
        context_label = "Custom topic/idea to build the post around:"
        persona = "You are a Senior Technologist and Engineering Leader with 10+ years of experience in software development, cybersecurity, and tech leadership."
    else:
        context_label = "Latest technology and industry news context:"
        persona = "You are a Senior Technologist and Engineering Leader with 10+ years of experience in software development, cybersecurity, and tech leadership."

    base_prompt = f"""{persona}

Your task is to write ONE LinkedIn post for today.

Today's date: {datetime.now().strftime('%B %d, %Y')}
Today is {day_name}, so the post style MUST be: {style}

{context_label}
{content}

STRICT RULES:
- Start with a powerful hook (shocking stat, bold question, or surprising fact)
- Length: {POST_MIN_WORDS}-{POST_MAX_WORDS} words only
- Tone: professional but human — like a real practitioner and leader, not a corporate bot
- Include ONE actionable tip or insight professionals can use TODAY
- NO hashtags in the body (they are added automatically later)
- USE EMOJIS — they are REQUIRED. Use 3–6 emojis throughout the post placed naturally (e.g., 💡 before insights, 🚀 for momentum, 🛡️ for security, 🔥 for urgency, ✅ for action items). Emojis must feel intentional, not decorative noise.
- NO phrases like "In today's digital landscape" or "In conclusion"
- DO NOT mention AI or that this was generated
- Write in first person ("I", "we", "our team")

"""

    format_1 = """DESIGN & FORMATTING RULE (The "Storytelling Narrative"):
- Open with a vivid, first-person scene-setter — paint a picture of a real moment (e.g., "It was 2 AM. Our prod database was down and no one knew why.").
- Use short punchy paragraphs (1-2 sentences max) separated by blank lines to build tension and pacing.
- Include an emoji at the start of key scene-shift paragraphs to guide the eye (e.g., 🔍 for investigation, 💥 for the turning point, 💡 for the lesson).
- End with a single, resonating takeaway line, then a reflective open question to the reader.
- DO NOT use bullet points or headers — this is pure narrative flow.
"""

    format_2 = """DESIGN & FORMATTING RULE (The "X Things I Learned" List):
- Start with a bold hook line, e.g. "5 brutal truths I learned after [doing X]:"
- Use a numbered list (1. 2. 3. ...) with 4–6 items. Each item MUST:
    • Start with a relevant emoji (e.g., 🔥, ✅, ⚠️, 💡, 🚀, 🎯)
    • Have a bold 2-5 word label in CAPS or bold, followed by a colon
    • Have a 1-2 sentence explanation
- Keep each list item punchy and standalone — zero fluff.
- End with a 1-line call-to-action or reflective question.
"""

    format_3 = """DESIGN & FORMATTING RULE (The "Controversial Take"):
- Start with a bold, 1-sentence statement paragraph that challenges common thinking — open with a 🔥 or ⚡ emoji.
- Use explicit "Myth vs Reality" or "Why everyone is wrong about" phrasing.
- Heavily use single-sentence paragraphs with wide line breaks for dramatic effect.
- Add emojis (🚫, ✅, 💡, 👇) to emphasize contrast and key turns.
- DO NOT use bullet points unless absolutely necessary.
"""

    format_4 = """DESIGN & FORMATTING RULE (The "Data Dump / Report"):
- Make the post extremely scannable like an executive briefing.
- Start with a "📌 TL;DR:" section at the very top, followed by a blank line.
- Use structured sections with all-caps emoji-prefixed headers (e.g., "📊 THE NUMBERS:", "⚠️ THE RISK:", "✅ THE FIX:").
- Heavily utilize data points, metrics, and statistics (pulled accurately from context).
- Use emojis as visual anchors before every section header and key stat.
"""

    format_5 = """DESIGN & FORMATTING RULE (The "Standard" Bullet Format):
- Use bullet points (•) and short paragraphs to make the post highly readable and scannable.
- Place a relevant emoji before 2-3 key bullets to draw attention.
- End the main text with an engaging "Poll-style" question with a 🗳️ emoji. 
- Provide 2–3 numbered emoji options for people to vote on in the comments. (e.g., "Reply with 1️⃣ for Yes, 2️⃣ for No, 3️⃣ for Maybe.")
"""

    format_6 = """DESIGN & FORMATTING RULE (The "Mini Thread" Style):
- Structure the post like a Twitter/X thread condensed into one LinkedIn post.
- Open with a teaser + 🧵 emoji, e.g.: "I broke down X so you don't have to. 🧵 A quick thread:"
- Use numbered thread entries: "1/", "2/", "3/" etc. (4–6 entries total), each on its own paragraph.
- Start each entry with a mini-headline as the first sentence (bold idea/conclusion first), then 1-sentence elaboration.
- Add a relevant emoji to each thread entry (🔍, 💡, ⚡, 🛡️, 🚀, ✅).
- Close with "That's a wrap. What's your take? 👇" or similar.
"""

    format_options = [format_1, format_2, format_3, format_4, format_5, format_6]
    selected_format = random.choice(format_options)


    news_rules = """FACTUAL ACCURACY RULES (CRITICAL):
- ONLY reference news stories, projects, or incidents that are listed in the VERIFIED NEWS section above
- DO NOT invent statistics, company names, or incident details
- If you cite a number or percentage, it must come directly from the provided news context
- If the news context is insufficient or irrelevant to today's theme, write the post based on general well-known tech principles, open-source knowledge, and your practitioner experience — do NOT fabricate specific events
- When in doubt, be general and insightful rather than specific and fabricated.

SOURCE LINK REQUIREMENT:
- You MUST include a source link at the absolute bottom of the post.
- Extract the single most relevant URL from the "Latest technology and industry news context" provided above.
- Format it exactly like this at the end of your response: "🔗 Source: [URL]"
"""

    custom_rules = """CUSTOM TOPIC RULES:
- The user has provided a specific custom topic or idea above.
- Build the entire post around this core idea, expanding on it using your expert persona.
- You do NOT need to cite news sources, write freely and insightfully based on the idea.
- Do NOT add a "🔗 Source:" link at the bottom unless the user explicitly included a URL in their custom idea prompt.
"""

    cve_rules = """LIVE THREAT INTEL RULES (CRITICAL):
- You MUST write a highly technical, urgent breakdown of ONE of the vulnerabilities in the context above.
- Choose the most severe or interesting CVE from the list provided.
- Explain WHAT the vulnerability is, HOW it might be exploited in the wild, and EXACT mitigation steps for security teams.
- DO NOT invent CVE details. Stick exactly to the provided description, product, and required action.
- End the post by explicitly providing the "🔗 Source: [Source Link]" exactly as it appears in the context for the chosen CVE.
"""

    knowledge_rules = """PERSONAL BRAIN RULES:
- The context above is lifted DIRECTLY from your "Personal Brain" (your private notes, code snippets, incident write-ups, or architecture plans).
- Use this context as the core foundation of your post. Share it as an authentic "behind-the-scenes" look, a lesson learned, or a thought-leadership stance.
- DO NOT summarize it like a news article. Discuss it as if it's a project you are currently working on or a problem you just solved.
- Frame it naturally e.g. "I was reviewing some architecture today and realized..." or "A snippet from my notes on..."
- Do NOT include any source links at the bottom.
"""

    end_prompt = """
Output ONLY the post text. Nothing else. No labels, no preamble."""

    if is_cve:
        selected_rules = cve_rules
    elif is_knowledge:
        selected_rules = knowledge_rules
    elif is_custom:
        selected_rules = custom_rules
    else:
        selected_rules = news_rules

    return base_prompt + selected_format + selected_rules + end_prompt

