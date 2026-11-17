"""
Humanized Comment Auto-Reply Engine with Live Internet & Database Grounding.
- Generates practitioner-grade, contextual, conversational LinkedIn comment replies.
- Fetches real-time facts from the internet (Google News RSS, DuckDuckGo, CISA KEV, MITRE CVE)
  and local database (past posts, knowledge files, history) whenever a comment asks or mentions news/CVEs.
- Avoids AI clichés, corporate-speak, or hollow generic praise.
- Anti-Abuse & Anti-Troll Filter: Drops toxic, vulgar, or baiting comments.
- Anti-Double-Comment / Deduplication: Never replies twice to the same comment or target URN.
- Connection / Self Whitelist: Never auto-replies to yourself, close team members, or listed connections.
- Quality Gate: Rejects short, robotic, dry, or hollow one-word responses.
- Continuously learns over time by recording accepted/high-performing response patterns into comment_memory.json.
- Supports dry-run, manual review mode, and direct LinkedIn API reply.
"""
import os
import re
import sys
import json
import random
import yaml
import argparse
import requests
import feedparser
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import LINKEDIN_ACCESS_TOKEN, LINKEDIN_PERSON_URN
from generate_post import _call_groq_with_retries

ROOT_DIR = Path(__file__).parent.parent
COMMENT_MEMORY_FILE = ROOT_DIR / "comment_memory.json"
POSTS_DIR = ROOT_DIR / "posts"
KNOWLEDGE_DIR = ROOT_DIR / "knowledge"
HISTORY_FILE = ROOT_DIR / "history.json"
IGNORED_CONNECTIONS_FILE = ROOT_DIR / "ignored_connections.yml"


# ============================================================
# 1. SAFETY, DEDUPLICATION & CONNECTION FILTERING
# ============================================================

def load_ignored_connections() -> List[str]:
    """Load profile handles, URNs, and names of connections to never reply to."""
    default_ignored = ["Raj Shevde", "Raj", "rajshevde", "tOvY-cGlm1", "urn:li:person:tOvY-cGlm1"]
    if not IGNORED_CONNECTIONS_FILE.exists():
        return default_ignored

    try:
        with open(IGNORED_CONNECTIONS_FILE, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if isinstance(data, dict) and "IGNORE_AUTHORS" in data:
                return [str(x).strip().lower() for x in data["IGNORE_AUTHORS"] if x]
    except Exception:
        pass
    return [x.lower() for x in default_ignored]


def is_ignored_author(author_name: str, target_urn: str = "") -> bool:
    """Check if the comment author is the user or in the ignored connections list."""
    if not author_name and not target_urn:
        return False

    ignored = load_ignored_connections()
    author_lower = author_name.lower().strip()
    urn_lower = target_urn.lower().strip()

    for entry in ignored:
        if entry in author_lower or (urn_lower and entry in urn_lower):
            return True
    return False


def is_already_replied(comment_text: str, target_urn: str = "") -> bool:
    """Check memory to prevent replying twice to the same comment or target URN."""
    memory = load_comment_memory()
    comment_clean = comment_text.strip().lower()
    urn_clean = target_urn.strip().lower()

    for item in memory.get("reply_history", []):
        if target_urn and item.get("target_urn") and item.get("target_urn").lower() == urn_clean:
            return True
        if item.get("comment", "").strip().lower() == comment_clean:
            return True
    return False


ABUSIVE_OR_TOXIC_TERMS = {
    "idiot", "stupid", "moron", "scam", "scammer", "fraud", "clown", "trash", "bullshit",
    "stfu", "shut up", "fuck", "bitch", "asshole", "retard", "fucking", "crap", "fake",
    "bot garbage", "worthless", "loser"
}

def contains_abusive_content(text: str) -> bool:
    """Detect toxic, abusive, or hostile language to ignore trolls."""
    lowered = text.lower()
    tokens = set(re.findall(r'\b\w+\b', lowered))
    return bool(tokens & ABUSIVE_OR_TOXIC_TERMS)


DRY_OR_HOLLOW_PHRASES = [
    "i agree", "spot on", "great post", "nice post", "thanks for sharing",
    "good insight", "well said", "interesting", "true that", "totally agree",
    "couldn't agree more", "100%", "fair point", "agreed"
]

def is_dry_or_robotic_reply(reply: str) -> bool:
    """Filter out dry, dismissive, or robotic one-liners."""
    words = reply.strip().split()
    if len(words) < 8:
        return True

    clean = re.sub(r'[^\w\s]', '', reply).strip().lower()
    for dry in DRY_OR_HOLLOW_PHRASES:
        if clean == dry or clean.startswith(f"{dry} "):
            # If it's just a hollow phrase with little substance (< 12 words)
            if len(words) < 14:
                return True
    return False


# ============================================================
# 2. DATABASE & REPO SEARCH
# ============================================================

def search_local_database(keywords: List[str]) -> List[str]:
    """Search previous posts and local knowledge files for relevant context."""
    matches = []
    if not keywords:
        return matches

    clean_keywords = [k.lower() for k in keywords if len(k) > 3]
    if not clean_keywords:
        return matches

    # 1. Search recent posts
    if POSTS_DIR.exists():
        post_files = sorted(list(POSTS_DIR.glob("*.md")), reverse=True)[:35]
        for post_file in post_files:
            try:
                content = post_file.read_text(encoding="utf-8")
                score = sum(1 for kw in clean_keywords if kw in content.lower())
                if score >= 1:
                    first_few_lines = "\n".join([line for line in content.splitlines() if line.strip()][:5])
                    matches.append(f"[Local Post DB - {post_file.name}]:\n{first_few_lines}")
                    if len(matches) >= 2:
                        break
            except Exception:
                continue

    # 2. Search knowledge base
    if KNOWLEDGE_DIR.exists():
        for kfile in KNOWLEDGE_DIR.rglob("*"):
            if kfile.is_file() and kfile.suffix in {".md", ".txt", ".json"}:
                try:
                    content = kfile.read_text(encoding="utf-8")
                    score = sum(1 for kw in clean_keywords if kw in content.lower())
                    if score >= 1:
                        matches.append(f"[Knowledge DB - {kfile.name}]:\n{content[:300]}")
                        if len(matches) >= 3:
                            break
                except Exception:
                    continue

    return matches


# ============================================================
# 3. LIVE INTERNET SEARCH & CVE GROUNDING
# ============================================================

def fetch_cve_details(cve_id: str) -> Optional[str]:
    """Fetch live CVE description from MITRE / CVE.org API."""
    try:
        url = f"https://cveawg.mitre.org/api/cve/{cve_id.upper()}"
        res = requests.get(url, timeout=6)
        if res.status_code == 200:
            data = res.json()
            containers = data.get("containers", {}).get("cna", {})
            title = containers.get("title", "")
            descriptions = containers.get("descriptions", [{}])
            desc_text = descriptions[0].get("value", "") if descriptions else ""
            return f"[CVE Details: {cve_id.upper()}] {title} - {desc_text[:350]}"
    except Exception:
        pass
    return None


def fetch_internet_news(query: str, max_results: int = 3) -> List[str]:
    """Search Google News RSS and DuckDuckGo for live internet context."""
    results = []
    encoded_q = urllib.parse.quote(query)

    # 1. Google News RSS search
    try:
        news_url = f"https://news.google.com/rss/search?q={encoded_q}&hl=en-US&gl=US&ceid=US:en"
        feed = feedparser.parse(news_url)
        for entry in feed.entries[:max_results]:
            title = entry.get("title", "")
            pub_date = entry.get("published", "")
            if title:
                results.append(f"[Live News - {pub_date}]: {title}")
    except Exception as e:
        print(f"[WARN] Failed Google News RSS search: {e}")

    # 2. DuckDuckGo Instant Answer / Abstract fallback
    if len(results) < 2:
        try:
            ddg_url = f"https://api.duckduckgo.com/?q={encoded_q}&format=json&no_html=1"
            res = requests.get(ddg_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if res.status_code == 200:
                data = res.json()
                abstract = data.get("AbstractText")
                heading = data.get("Heading")
                if abstract:
                    results.append(f"[DDG Fact - {heading}]: {abstract[:300]}")
        except Exception as e:
            print(f"[WARN] Failed DuckDuckGo fetch: {e}")

    return results


def extract_search_intent(comment_text: str) -> Tuple[bool, str, Optional[str]]:
    """Detect if the comment is asking about or discussing news, current events, CVEs, or tools."""
    cve_match = re.search(r'\bCVE[-_ ](\d{4})[-_ ](\d{4,7})\b', comment_text, re.IGNORECASE)
    cve_id = None
    if cve_match:
        cve_id = f"CVE-{cve_match.group(1)}-{cve_match.group(2)}"

    news_triggers = [
        "news", "latest", "recent", "heard about", "did you see", "today", "yesterday",
        "breach", "outage", "patch", "zero day", "0-day", "exploit", "cve", "advisory",
        "released", "announced", "update", "hacked", "leak", "ransomware", "what happened with",
        "thoughts on the", "have you heard"
    ]
    
    text_lower = comment_text.lower()
    needs_search = bool(cve_id) or any(t in text_lower for t in news_triggers) or "?" in comment_text

    cleaned = re.sub(r'[^\w\s-]', ' ', comment_text).strip()
    words = [w for w in cleaned.split() if len(w) > 3 and w.lower() not in {"what", "your", "this", "that", "about", "have", "with", "from"}]
    search_query = " ".join(words[:6]) if words else comment_text[:50]

    return needs_search, search_query, cve_id


def gather_grounding_context(comment_text: str, post_context: str = "") -> str:
    """Gather live internet and local database information if relevant to the comment."""
    needs_search, search_query, cve_id = extract_search_intent(comment_text)
    if not needs_search:
        return ""

    context_snippets = []

    # A. Specific CVE lookup
    if cve_id:
        print(f"[INFO] Detected CVE '{cve_id}'. Fetching official threat intelligence...")
        cve_info = fetch_cve_details(cve_id)
        if cve_info:
            context_snippets.append(cve_info)

    # B. Internet News search
    print(f"[INFO] Querying internet for: '{search_query}'...")
    news_items = fetch_internet_news(search_query, max_results=3)
    if news_items:
        context_snippets.extend(news_items)

    # C. Local database / previous posts search
    keywords = search_query.split()
    local_hits = search_local_database(keywords)
    if local_hits:
        context_snippets.extend(local_hits)

    if not context_snippets:
        return ""

    return "\n".join(context_snippets)


# ============================================================
# 4. SELF-LEARNING COMMENT MEMORY
# ============================================================

def load_comment_memory() -> Dict[str, Any]:
    """Load learned reply patterns and past interactions."""
    default = {
        "style_guidelines": [
            "Keep replies concise: 1 to 4 sentences maximum.",
            "Always acknowledge the specific technical point or news event the commenter brought up.",
            "Write in natural first person ('In our testing', 'Saw the advisory', 'We looked into that').",
            "Cite concrete operational facts or nuance rather than hand-waving.",
            "End with a thought-provoking conversational hook or open reflection when appropriate.",
            "Zero corporate fluff: Never use 'Thanks for sharing!', 'Great insight!', or 'Couldn't agree more!'"
        ],
        "exemplars": [
            {
                "comment": "Did you see the recent Fortinet RCE news?",
                "reply": "Yeah, CVE-2024-21762 was nasty because it allowed unauthenticated RCE via crafted HTTP requests. If teams didn't disable web SSL-VPN or patch immediately, attackers had persistence within hours."
            },
            {
                "comment": "Most teams ignore SIEM tuning and then wonder why analyst burnout is so high.",
                "reply": "Spot on. In our SOC, alert fatigue dropped 40% only after we treated alert rules like production code with mandatory deprecation reviews."
            },
            {
                "comment": "Is Zero Trust really feasible for legacy environments without breaking operations?",
                "reply": "It's painful upfront if you try boiling the ocean. We found isolating critical crown jewels with identity proxies first gives 80% of the defense before even touching the legacy core."
            }
        ],
        "reply_history": []
    }
    if not COMMENT_MEMORY_FILE.exists():
        return default
    try:
        with open(COMMENT_MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "exemplars" not in data:
                data["exemplars"] = default["exemplars"]
            if "reply_history" not in data:
                data["reply_history"] = []
            return data
    except Exception:
        return default


def save_comment_memory(memory: Dict[str, Any]):
    """Persist learned reply memory."""
    if len(memory.get("reply_history", [])) > 150:
        memory["reply_history"] = memory["reply_history"][-150:]
    with open(COMMENT_MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)


# ============================================================
# 5. DYNAMIC & HUMANIZED AI REPLY GENERATION
# ============================================================

PERSONA_ANGLES = [
    {
        "role": "Field Incident Responder",
        "flavor": "Direct, operational, battle-tested. Focus on triage reality, late-night fixes, and practical edge-cases."
    },
    {
        "role": "Pragmatic Security Architect",
        "flavor": "Systemic yet realistic. Balances risk reduction vs developer friction and business velocity."
    },
    {
        "role": "Threat Hunter / Red Teamer",
        "flavor": "Curious, slightly skeptical, looks at attacker economics and what actually bypasses standard controls."
    },
    {
        "role": "Peer Engineering Colleague",
        "flavor": "Casual Slack-like technical discussion, validating genuine tradeoffs and asking sharp follow-ups."
    }
]

REPLY_FORMAT_STYLES = [
    "A direct observation followed by a counter-intuitive operational lesson (2 sentences).",
    "A quick war-story snippet from past incidents, concluding with a conversational question (2-3 sentences).",
    "Validating their specific constraint, then highlighting an attacker pivot point people usually miss (2 sentences).",
    "A concise, punchy technical breakdown with zero filler (1-2 sentences)."
]


def generate_humanized_reply(post_context: str, comment_text: str, commenter_name: str = "") -> str:
    """Generate a dynamically styled, highly conversational, non-robotic reply grounded in facts."""
    memory = load_comment_memory()
    exemplars = memory.get("exemplars", [])

    # Pick dynamic persona angle and format style
    persona = random.choice(PERSONA_ANGLES)
    format_style = random.choice(REPLY_FORMAT_STYLES)
    dynamic_temperature = round(random.uniform(0.72, 0.88), 2)

    sample_exemplars = []
    if exemplars:
        sample_count = min(3, len(exemplars))
        sample_exemplars = random.sample(exemplars, sample_count)

    exemplars_prompt = ""
    if sample_exemplars:
        exemplars_prompt = "\n".join(
            [f"- Comment: \"{e['comment']}\"\n  Reply: \"{e['reply']}\"" for e in sample_exemplars]
        )

    # Gather live facts from internet and local knowledge database
    grounding_data = gather_grounding_context(comment_text, post_context)
    grounding_prompt = ""
    if grounding_data:
        grounding_prompt = f"""
LIVE INTERNET NEWS & DATABASE GROUNDING FACTS:
{grounding_data}
(Weave these concrete facts naturally into the response if answering news/CVE/incident questions. Avoid copy-pasting raw text.)
"""

    prompt = f"""You are a senior cybersecurity engineer having a quick, natural conversation under a LinkedIn post.

YOUR MINDSET FOR THIS SPECIFIC REPLY:
- Angle: {persona['role']} ({persona['flavor']})
- Format Structure: {format_style}

ORIGINAL POST CONTEXT:
{post_context[:450]}

COMMENT RECEIVED:
{f'From: {commenter_name}' if commenter_name else ''}
"{comment_text}"
{grounding_prompt}
REFERENCE NATURAL DIALOGUE EXAMPLES:
{exemplars_prompt}

CRITICAL RULES TO AVOID LOOKING LIKE AN AI BOT OR DRY ROBOT:
1. DYNAMIC & NATURAL: Write like an authentic human texting an engineering peer on Slack or LinkedIn.
2. STRICT BANS (Instant Failures):
   - NEVER start with: "Yes,", "I agree,", "Spot on,", "Great point,", "Thanks for sharing,", "Good question,", "In today's landscape,"
   - NEVER sound like a customer support rep, advisory bot, or automated assistant.
   - NO DRY ONE-LINERS: Never return dry replies like "Agreed", "True", or generic fluff like "I recommend patching".
3. Provide real-world technical insight or an operational edge-case.
4. Length: 2 to 3 substantive sentences (30 to 65 words). Be punchy, vivid, and authentic.

Output ONLY the raw reply text. No quotation marks, no preamble, no commentary."""

    for attempt in range(2):
        try:
            reply = _call_groq_with_retries(prompt, temperature=dynamic_temperature).strip()
            if reply.startswith('"') and reply.endswith('"'):
                reply = reply[1:-1].strip()
            for bad_prefix in ["Here is", "Reply:", "Response:"]:
                if reply.startswith(bad_prefix):
                    reply = reply.split(":", 1)[-1].strip()

            # Ensure it is not a dry or hollow response
            if not is_dry_or_robotic_reply(reply):
                return reply
            print("[WARN] Generated reply was too dry or short. Regenerating...")
        except Exception as e:
            print(f"[ERROR] Failed to generate AI reply attempt {attempt}: {e}")

    return "From what we've seen in triage, the initial infection path is rarely where the major loss occurs—it is almost always the ungoverned service accounts with excessive domain permissions."


def record_successful_interaction(comment_text: str, reply_text: str, target_urn: str = "", quality_score: int = 5):
    """Save the interaction to memory and learn high-quality pairs as new exemplars."""
    memory = load_comment_memory()
    entry = {
        "comment": comment_text,
        "reply": reply_text,
        "target_urn": target_urn,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "quality_score": quality_score
    }
    memory["reply_history"].append(entry)

    # Promote to exemplars if quality score is high
    if quality_score >= 4:
        if not any(e["comment"] == comment_text for e in memory.get("exemplars", [])):
            memory.setdefault("exemplars", []).append({
                "comment": comment_text,
                "reply": reply_text
            })
            if len(memory["exemplars"]) > 15:
                memory["exemplars"] = memory["exemplars"][-15:]

    save_comment_memory(memory)
    print(f"[SUCCESS] Recorded and learned from reply interaction (Exemplars count: {len(memory['exemplars'])}).")


def post_reply_to_linkedin(target_urn: str, reply_text: str) -> bool:
    """Post comment reply to LinkedIn via REST API."""
    if not LINKEDIN_ACCESS_TOKEN or not LINKEDIN_PERSON_URN:
        print("[ERROR] LINKEDIN_ACCESS_TOKEN or LINKEDIN_PERSON_URN not configured.")
        return False

    encoded_urn = urllib.parse.quote(target_urn, safe="")
    url = f"https://api.linkedin.com/rest/socialActions/{encoded_urn}/comments"
    headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "LinkedIn-Version": "202601",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json"
    }
    payload = {
        "actor": LINKEDIN_PERSON_URN,
        "object": target_urn,
        "message": {
            "text": reply_text
        }
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code == 201:
            print(f"[SUCCESS] Published reply on LinkedIn to {target_urn}")
            return True
        else:
            print(f"[WARN] LinkedIn Comments API returned {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        print(f"[ERROR] Failed to post reply to LinkedIn: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Humanized & Fact-Grounded Auto-Reply Engine")
    parser.add_argument("--post", default="", help="Context/topic of the post")
    parser.add_argument("--comment", required=True, help="The incoming comment text to reply to")
    parser.add_argument("--author", default="", help="Name of the commenter")
    parser.add_argument("--target-urn", default="", help="LinkedIn URN of post or comment to reply to")
    parser.add_argument("--score", type=int, default=5, help="Self-learning quality score (1-5)")
    parser.add_argument("--auto-publish", action="store_true", help="Attempt direct LinkedIn publication")
    args = parser.parse_args()

    # Rule 1: Never reply to yourself or ignored connections
    if is_ignored_author(args.author, args.target_urn):
        print(f"[SKIP] Comment author '{args.author}' matches yourself or your connected profile list. Skipping auto-reply.")
        return

    # Rule 2: Never double comment / reply to the same interaction twice
    if is_already_replied(args.comment, args.target_urn):
        print("[SKIP] Already replied to this comment previously. Skipping duplicate reply.")
        return

    # Rule 3: Skip abusive, toxic, or troll comments
    if contains_abusive_content(args.comment):
        print("[SKIP] Comment contains abusive or hostile language. Skipping auto-reply.")
        return

    print(f"[INFO] Analyzing incoming comment from '{args.author or 'Colleague'}':\n\"{args.comment}\"\n")
    reply = generate_humanized_reply(args.post, args.comment, args.author)

    # Rule 4: Quality gate against dry replies
    if is_dry_or_robotic_reply(reply):
        print("[SKIP] Output was too dry or brief. Skipping auto-reply to preserve human quality.")
        return

    print("=" * 60)
    print(f"🤖 HUMANIZED GENERATED REPLY:\n{reply}")
    print("=" * 60)

    # Self-learning loop
    record_successful_interaction(args.comment, reply, target_urn=args.target_urn, quality_score=args.score)

    if args.auto_publish and args.target_urn:
        print("[INFO] Attempting to publish reply to LinkedIn...")
        post_reply_to_linkedin(args.target_urn, reply)


if __name__ == "__main__":
    main()
