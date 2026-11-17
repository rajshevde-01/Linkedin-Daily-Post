"""
Humanized Comment Auto-Reply Engine with Few-Shot Feedback Learning.
- Generates practitioner-grade, contextual, conversational LinkedIn comment replies.
- Avoids AI clichés, corporate corporate-speak, or hollow generic praise.
- Learns over time by recording accepted/high-performing response patterns into comment_memory.json.
- Supports dry-run, manual approval/input mode, and direct API reply (when Community Management API permissions are present).
"""
import os
import sys
import json
import argparse
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import LINKEDIN_ACCESS_TOKEN, LINKEDIN_PERSON_URN, GROQ_API_KEYS
from generate_post import _call_groq_with_retries

ROOT_DIR = Path(__file__).parent.parent
COMMENT_MEMORY_FILE = ROOT_DIR / "comment_memory.json"


def load_comment_memory() -> Dict[str, Any]:
    """Load learned reply patterns and past interactions."""
    default = {
        "style_guidelines": [
            "Keep replies concise: 1 to 4 sentences maximum.",
            "Always acknowledge the specific technical point the commenter made.",
            "Write in natural first person ('I agree', 'In our experience', 'That's a solid point').",
            "Offer a nuanced counter-perspective or an operational war-story snippet.",
            "End with a thought-provoking conversational hook or open reflection when appropriate.",
            "Zero corporate fluff: Never use 'Thanks for sharing!', 'Great insight!', or 'Couldn't agree more!'"
        ],
        "exemplars": [
            {
                "comment": "Most teams ignore SIEM tuning and then wonder why analyst burnout is so high.",
                "reply": "Spot on. In our SOC, alert fatigue dropped 40% only after we treated alert rules like production code with mandatory deprecation reviews."
            },
            {
                "comment": "Is Zero Trust really feasible for legacy environments without breaking operations?",
                "reply": "It's painful upfront if you try boiling the ocean. We found isolating critical crown jewels with identity proxies first gives 80% of the defense before even touching the legacy core."
            },
            {
                "comment": "CVE-2023-44487 rapid reset was crazy to mitigate at scale.",
                "reply": "The downstream proxy crashes were the real killer during that week. Disabling HTTP/2 on edge was the only viable 4 AM patch until vendors shipped binaries."
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
    # Keep last 150 reply history logs
    if len(memory.get("reply_history", [])) > 150:
        memory["reply_history"] = memory["reply_history"][-150:]
    with open(COMMENT_MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)


def generate_humanized_reply(post_context: str, comment_text: str, commenter_name: str = "") -> str:
    """Generate a highly conversational, expert-level reply to a LinkedIn comment."""
    memory = load_comment_memory()
    exemplars = memory.get("exemplars", [])

    exemplars_prompt = ""
    if exemplars:
        exemplars_prompt = "\n".join(
            [f"- Comment: \"{e['comment']}\"\n  Reply: \"{e['reply']}\"" for e in exemplars[-6:]]
        )

    prompt = f"""You are a veteran senior cybersecurity practitioner & incident responder replying to a comment on your LinkedIn post.

ORIGINAL POST TOPIC/SUMMARY:
{post_context[:600]}

COMMENT RECEIVED:
{f'From: {commenter_name}' if commenter_name else ''}
"{comment_text}"

PAST SUCCESSFUL CONVERSATION EXEMPLARS (Emulate this natural tone):
{exemplars_prompt}

HUMANIZATION & TONE RULES:
1. Speak peer-to-peer. You are chatting with another engineer or leader in the comments.
2. NO BOT-SPEAK: Banned words/phrases:
   - "Thanks for sharing!"
   - "Great comment!"
   - "Couldn't agree more!"
   - "Valuable insight"
   - "In today's landscape"
3. Directly engage with the substance of their argument or question.
4. Keep it tight: 1 to 3 punchy sentences (maximum 60 words).
5. If they disagree, validate the trade-off respectfully and offer an edge-case or nuance.
6. Tone: Humble, sharp, practical, battle-tested.

Output ONLY the reply text. No quotes, no prefix, no meta-commentary."""

    try:
        reply = _call_groq_with_retries(prompt, temperature=0.6).strip()
        # Clean quotes if model wrapped response
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
        # Check duplicate
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
    parser = argparse.ArgumentParser(description="Humanized Auto-Reply & Self-Learning Comment Engine")
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
