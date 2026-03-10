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
# Tier 1: Top-tier cybersecurity news
# Tier 2: Dedicated Threat Intel and Forensics
# Tier 3: Focused blogs and communities
RSS_FEEDS = [
    # Tier 1 — Broad Cybersecurity News
    {"url": "https://feeds.feedburner.com/TheHackersNews", "name": "The Hacker News", "tier": 1},
    {"url": "https://www.bleepingcomputer.com/feed/", "name": "BleepingComputer", "tier": 1},
    {"url": "https://www.darkreading.com/rss.xml", "name": "Dark Reading", "tier": 1},

    # Tier 2 — Threat Intel & Forensics
    {"url": "https://www.cisa.gov/uscert/ncas/current-activity.xml", "name": "CISA Current Activity", "tier": 2},
    {"url": "https://krebsonsecurity.com/feed/", "name": "Krebs on Security", "tier": 2},
    {"url": "https://www.cybersecuritydive.com/feeds/news/", "name": "Cybersecurity Dive", "tier": 2},

    # Tier 3 — Expert Blogs & Deep Tech
    {"url": "https://portswigger.net/daily-swig/rss", "name": "The Daily Swig", "tier": 3},
    {"url": "https://news.ycombinator.com/rss", "name": "Hacker News (YC)", "tier": 3},
]

# --- Day-of-Week Rotation ---
DAY_STYLES = {
    0: "SOC (Security Operations Center) Operations & Analysts",
    1: "VAPT (Vulnerability Assessment & Penetration Testing)",
    2: "Digital Forensics & Incident Response (DFIR)",
    3: "Global Cyber Attacks & Threat Intelligence",
    4: "Week in review — Major Cybersecurity Breaches",
    5: "Cybersecurity Career Advice & Certifications",
    6: "Open Source Security Tools & Frameworks",
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
        persona = "You are a Senior Cybersecurity Architect and DFIR Specialist sharing a genuine insight directly derived from your personal work/notes."
    elif is_custom:
        context_label = "Custom topic/idea to build the post around:"
        persona = "You are a Senior Cybersecurity Architect and Threat Intelligence Leader with 10+ years of experience in SOC, VAPT, and Digital Forensics."
    else:
        context_label = "Latest cybersecurity and threat intelligence context:"
        persona = "You are a Senior Cybersecurity Architect and Threat Intelligence Leader with 10+ years of experience in SOC, VAPT, and Digital Forensics."

    base_prompt = f"""{persona}

Your task is to write ONE LinkedIn post for today.

Today's date: {datetime.now().strftime('%B %d, %Y')}
Today is {day_name}, so the post style MUST be: {style}

{context_label}
{content}

STRICT RULES:
- Length: {POST_MIN_WORDS}-{POST_MAX_WORDS} words only
- NO hashtags in the body (they are added automatically later)
- NO phrases like "In today's digital landscape", "In conclusion", or "Delving into"
- DO NOT mention AI or that this was generated
- Write in first person ("I", "we", "our team")

CREATIVITY & TONE RULES:
- AVOID sounding like a generic corporate thought leader. Write like a real practitioner talking to a colleague on Slack, or writing a personal developer blog.
- Vary your sentence length dramatically. Use powerful 3-word sentences. Then use longer, flowing explanatory sentences. Disrupt the typical "AI cadence" by being punchy and unpredictable.
- Emojis are allowed, but do NOT force a specific number. Use them organically where they fit the specific style below.
"""

    format_1 = """DESIGN & FORMATTING RULE (The "War Story"):
- Style: A dramatic, first-person narrative. Almost like a journal entry.
- Opening: Drop the reader immediately into a stressful or active scene (e.g., "It was 2 AM and the alerts wouldn't stop." or "I just stared at the packet capture for 10 minutes.").
- Formatting: Use short, punchy paragraphs separated by blank lines. ZERO bullet points.
- Tone: Exhausted but victorious, or highly reflective. Speak purely from experience.
- Closing: A single-sentence profound takeaway.
"""

    format_2 = """DESIGN & FORMATTING RULE (The "Unpopular Opinion"):
- Style: Highly argumentative, punchy, and slightly controversial within the security space.
- Opening: Start with a bold, 1-sentence statement that challenges common thinking (e.g., "Stop telling people to just 'patch faster'. It's lazy advice." or "Most IOC feeds are garbage.").
- Formatting: Heavily use single-sentence paragraphs with wide line breaks for dramatic effect. Contrast "What people think" vs. "What actually happens".
- Tone: Sharp, direct, zero fluff.
- Closing: Challenge the audience to disagree with you in the comments.
"""

    format_3 = """DESIGN & FORMATTING RULE (The "Cheat Sheet"):
- Style: Highly structured, scannable, and bookmarkable reference guide.
- Opening: "The ultimate cheat sheet for [Topic]:" or "Everything you need to know about [Event], summarized in 30 seconds:"
- Formatting: Use a tight, numbered or bulleted list. Start each bullet with an emoji (e.g., 📌, ⚠️, ✅, 🛡️, 🔍), followed by a 2-4 word bold label, then a 1-sentence explanation.
- Tone: Academic, helpful, and concise. Make it easy to screenshot.
"""

    format_4 = """DESIGN & FORMATTING RULE (The "Technical Deep-Dive"):
- Style: Dense, highly technical, and analytical. Written for senior engineers.
- Formatting: Use backticks (`code`) for technical terms, IPs, CVSS scores, or malware names. Break the post down into explicit mini-sections: "The Vector", "The Exploit", and "The Mitigation".
- Tone: Analytical, dry, and brutally factual. Assume the reader is already a security expert. No generic advice.
- Closing: Provide one highly specific detection rule or technical action item.
"""

    format_5 = """DESIGN & FORMATTING RULE (The "Ask the Community" Poll):
- Style: Short, conversational, and designed purely to generate debate.
- Opening: State a recent event, finding, or security dilemma in 2-3 sentences max.
- Formatting: Ask a direct question, then provide 3 numbered options for people to vote on. (e.g., "1️⃣ Keep the legacy system, 2️⃣ Rip and replace, 3️⃣ Build a proxy layer.")
- Tone: Curious and open-minded. You are asking for advice/opinions, not giving it.
"""

    format_6 = """DESIGN & FORMATTING RULE (The "Day in the Life" Insight):
- Style: Extremely casual, like a quick Slack message to a coworker or a thought you had while brewing coffee.
- Opening: Start with a casual, over-the-shoulder observation (e.g., "Currently digging through a massive log file and realized..." or "Just wrapped up a post-mortem call and wanted to vent/share something.").
- Formatting: Very natural prose. 1 or 2 medium-length paragraphs. No forced listicles.
- Tone: Relaxed, colloquial, and authentic. 
- Closing: Just a casual sign-off or an open thought.
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

