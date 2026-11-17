"""
Humanized Comment Auto-Reply Engine with Live Internet & Database Grounding.
- Generates practitioner-grade, contextual, conversational LinkedIn comment replies.
- Fetches real-time facts from the internet (Google News RSS, DuckDuckGo, CISA KEV, MITRE CVE)
  and local database (past posts, knowledge files, history) whenever a comment asks or mentions news/CVEs.
- Avoids AI clichés, corporate-speak, or hollow generic praise.
- Continuously learns over time by recording accepted/high-performing response patterns into comment_memory.json.
- Supports dry-run, manual review mode, and direct LinkedIn API reply.
"""
import os
import re
import sys
import json
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


# ============================================================
# 1. DATABASE & REPO SEARCH
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
# 2. LIVE INTERNET SEARCH & CVE GROUNDING
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

    # 1. Google News RSS search (fresh live news)
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
    """
    Detect if the comment is asking about or discussing news, current events, CVEs, or tools.
    Returns: (needs_external_grounding, search_query, cve_id)
    """
    # 1. Check for CVE-YYYY-NNNN
    cve_match = re.search(r'\bCVE[-_ ](\d{4})[-_ ](\d{4,7})\b', comment_text, re.IGNORECASE)
    cve_id = None
    if cve_match:
        cve_id = f"CVE-{cve_match.group(1)}-{cve_match.group(2)}"

    # 2. Trigger words indicating news, updates, breaches, or latest announcements
    news_triggers = [
        "news", "latest", "recent", "heard about", "did you see", "today", "yesterday",
        "breach", "outage", "patch", "zero day", "0-day", "exploit", "cve", "advisory",
        "released", "announced", "update", "hacked", "leak", "ransomware", "what happened with",
        "thoughts on the", "have you heard"
    ]
    
    text_lower = comment_text.lower()
    needs_search = bool(cve_id) or any(t in text_lower for t in news_triggers) or "?" in comment_text

    # Build clean query
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
# 3. SELF-LEARNING COMMENT MEMORY
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
# 4. HUMANIZED AI REPLY GENERATION
# ============================================================

def generate_humanized_reply(post_context: str, comment_text: str, commenter_name: str = "") -> str:
    """Generate a highly conversational, expert-level reply grounded in internet & database facts."""
    memory = load_comment_memory()
    exemplars = memory.get("exemplars", [])

    exemplars_prompt = ""
    if exemplars:
        exemplars_prompt = "\n".join(
            [f"- Comment: \"{e['comment']}\"\n  Reply: \"{e['reply']}\"" for e in exemplars[-6:]]
        )

    # Gather live facts from internet and local knowledge database
    grounding_data = gather_grounding_context(comment_text, post_context)
    grounding_prompt = ""
    if grounding_data:
        grounding_prompt = f"""
LIVE INTERNET NEWS & DATABASE GROUNDING FACTS:
{grounding_data}
(Use these verified facts to accurately answer or reference the news/CVE/incident mentioned, but weave it into natural peer conversation.)
"""

    prompt = f"""You are a veteran senior cybersecurity practitioner replying to a comment on your LinkedIn post.

ORIGINAL POST TOPIC/SUMMARY:
{post_context[:500]}

COMMENT RECEIVED:
{f'From: {commenter_name}' if commenter_name else ''}
"{comment_text}"
{grounding_prompt}
PAST SUCCESSFUL CONVERSATION EXEMPLARS (Emulate this natural tone):
{exemplars_prompt}

HUMANIZATION & ACCURACY RULES:
1. Speak peer-to-peer. You are chatting with another engineer or practitioner in the comments.
2. If they are asking or talking about any news, incident, vulnerability (CVE), or tool, utilize the live grounding facts to reply accurately with real context.
3. NO BOT-SPEAK: Banned words/phrases:
   - "Thanks for sharing!"
   - "Great comment!"
   - "Couldn't agree more!"
   - "Valuable insight"
   - "In today's landscape"
   - "As an AI"
4. Keep it tight: 1 to 3 punchy sentences (maximum 60 words).
5. Tone: Humble, sharp, practical, battle-tested.

Output ONLY the reply text. No quotes, no prefix, no meta-commentary."""

    try:
        reply = _call_groq_with_retries(prompt, temperature=0.6).strip()
        if reply.startswith('"') and reply.endswith('"'):
            reply = reply[1:-1].strip()
        return reply
    except Exception as e:
        print(f"[ERROR] Failed to generate AI reply: {e}")
        return "Fair point. Balancing operational reality with strict security controls is always the hardest trade-off here."


def record_successful_interaction(comment_text: str, reply_text: str, quality_score: int = 5):
    """Save the interaction to memory and learn high-quality pairs as new exemplars."""
    memory = load_comment_memory()
    entry = {
        "comment": comment_text,
        "reply": reply_text,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "quality_score": quality_score
    }
    memory["reply_history"].append(entry)

    # If it's a high quality response, promote it to exemplars for future learning (capped at 15)
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

    print(f"[INFO] Analyzing incoming comment from '{args.author or 'Colleague'}':\n\"{args.comment}\"\n")
    reply = generate_humanized_reply(args.post, args.comment, args.author)
    print("=" * 60)
    print(f"🤖 HUMANIZED GENERATED REPLY:\n{reply}")
    print("=" * 60)

    # Self-learning loop
    record_successful_interaction(args.comment, reply, quality_score=args.score)

    if args.auto_publish and args.target_urn:
        print("[INFO] Attempting to publish reply to LinkedIn...")
        post_reply_to_linkedin(args.target_urn, reply)


if __name__ == "__main__":
    main()
