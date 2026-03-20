"""
Generate LinkedIn post using Google Gemini API.
"""
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
import re

# Add scripts dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    GROQ_API_KEYS, 
    get_system_prompt, 
    get_image_system_prompt,
    POST_MIN_WORDS, 
    POST_MAX_WORDS
)
from fetch_news import get_news_context
from fetch_cve import get_cve_context
from fetch_knowledge import fetch_random_knowledge
from history import add_to_history
from generate_image import generate_post_image

def generate_post(content: str, is_custom: bool = False, is_cve: bool = False, is_knowledge: bool = False) -> str:
    """Generate a LinkedIn post using Groq API."""
    try:
        from groq import Groq
    except ImportError:
        print("[ERROR] groq package not installed. Run: pip install groq")
        sys.exit(1)

    if not GROQ_API_KEYS:
        print("[ERROR] GROQ_API_KEY environment variable not set or invalid")
        sys.exit(1)

    system_prompt = get_system_prompt(content, is_custom=is_custom, is_cve=is_cve, is_knowledge=is_knowledge)

    # Added robust retry and fallback logic for Rate Limits / Quotas
    import time
    
    max_retries = 3
    models_to_try = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
    
    post_text = None
    last_error = None
    
    # Outer Loop: Try each model
    for current_model in models_to_try:
        if post_text is not None:
            break
            
        print(f"\n[INFO] Starting attempts with model {current_model}...")
        
        # Middle Loop: Try each API key for the current model
        for key_idx, api_key in enumerate(GROQ_API_KEYS):
            if post_text is not None:
                break
                
            print(f"[INFO] Using API key #{key_idx + 1}/{len(GROQ_API_KEYS)} for {current_model}...")
            client = Groq(api_key=api_key)
            
            # Inner Loop: Retries for temporary issues (like concurrent requests)
            for attempt in range(max_retries):
                try:
                    response = client.chat.completions.create(
                        model=current_model,
                        messages=[
                            {
                                "role": "user",
                                "content": system_prompt
                            }
                        ]
                    )
                    post_text = response.choices[0].message.content.strip()
                    print(f"[SUCCESS] Generation successful with {current_model} (Key #{key_idx + 1})")
                    break  # Success, break inner loop
                except Exception as e:
                    err_msg = str(e).lower()
                    last_error = e
                    
                    if "429" in err_msg or "too many requests" in err_msg or "quota" in err_msg or "401" in err_msg or "invalid_api_key" in err_msg:
                        print(f"[WARN] Quota exhausted or invalid key for {current_model} using Key #{key_idx + 1}: {e}")
                        # Immediately fail this key and move to the next key without retrying wait times
                        break 
                    else:
                        # Other non-quota errors (transient API issues)
                        if attempt < max_retries - 1:
                            print(f"[WARN] API Error. Waiting 10s before retry {attempt+1}/{max_retries}... Error: {e}")
                            time.sleep(10)
                        else:
                            print(f"[ERROR] Max retries reached for Key #{key_idx + 1}. Moving to next key/model.")
                            break
                            
    if post_text is None:
        print(f"\n[FATAL] Exhausted all {len(models_to_try)} models across all {len(GROQ_API_KEYS)} API keys.")
        print(f"[FATAL] Last error encountered: {last_error}")
        sys.exit(1)

    return post_text


def verify_post(post_text: str) -> str:
    """Perform a second-pass 'Sense Check' to remove AI-isms and improve flow."""
    from groq import Groq
    
    sense_check_prompt = f"""You are a brutal Executive Editor for a top-tier cybersecurity blog.
Review the LinkedIn post below. Your goal is to make it sound 100% like a human practitioner and 0% like an AI.

STRICT EDITING RULES:
1. **CUT THE FLUFF**: Remove generic 'AI-speak' (e.g., 'In world where...', 'Unlock potential', 'Comprehensive', 'Fast-paced'). If a sentence isn't adding technical value or a strong opinion, DELETE IT.
2. **KILLER HOOK**: Ensure the first line is a direct, jarring statement. If it starts with an introduction ("Let's dive into", "Today I'm looking at"), REWRITE to start with the core problem or fact.
3. **FLATTEN THE TONE**: If the text sounds like a corporate marketing pitch, make it dry, analytical, and practitioner-first.
4. **VARY SENTENCE LENGTH**: Ruthlessly enforce mixed lengths. Add 3-word sentences. Break up long clauses.
5. **NO CONCLUSION**: Delete any concluding summary paragraphs. The post should end on the CTA or raw takeaway.
6. **PRESERVE EXTRAS**: Keep hashtags and source links intact at the absolute bottom.

POST TO REVIEW:
{post_text}

Output ONLY the improved, finalized post text."""

    print("[INFO] Performing Multi-Model Sense Check...")
    # Use the fastest/cheapest model for the sense check
    try:
        client = Groq(api_key=GROQ_API_KEYS[0])
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": sense_check_prompt}]
        )
        verified_text = response.choices[0].message.content.strip()
        print("[SUCCESS] Sense Check complete.")
        return verified_text
    except Exception as e:
        print(f"[WARN] Sense Check failed ({e}). Using original post.")
        return post_text


def generate_image_prompt(post_text: str) -> str:
    """Generate a high-quality DALL-E prompt based on the post content."""
    from groq import Groq
    system_prompt = get_image_system_prompt(post_text)

    print("[INFO] Generating premium Image Prompt...")
    try:
        client = Groq(api_key=GROQ_API_KEYS[0])
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": system_prompt}]
        )
        image_prompt = response.choices[0].message.content.strip()
        print("[SUCCESS] Image Prompt generated.")
        return image_prompt
    except Exception as e:
        print(f"[WARN] Image Prompt generation failed ({e}).")
        return ""


def save_post(post_text: str, image_prompt: str, date_str: str, image_path: str = "") -> str:
    """Save post and image prompt to posts/ directory and return the file path."""
    posts_dir = Path(__file__).parent.parent / "posts"
    posts_dir.mkdir(exist_ok=True)

    index = 1
    filepath = posts_dir / f"{date_str}-{index}.md"
    while filepath.exists():
        index += 1
        filepath = posts_dir / f"{date_str}-{index}.md"

    content = f"""---
date: {date_str}
status: pending
style: {get_style_for_display()}
word_count: {len(post_text.split())}
generated_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
image_path: {image_path}
image_prompt: |
  {image_prompt}
---

{post_text}
"""
    filepath.write_text(content, encoding="utf-8")
    print(f"[INFO] Post saved to {filepath}")
    return str(filepath)


def get_style_for_display() -> str:
    """Get today's post style for metadata."""
    from config import get_today_style
    style, day = get_today_style()
    return f"{day}: {style}"


def main():
    parser = argparse.ArgumentParser(description="Generate daily LinkedIn post")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"),
                        help="Date for the post (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print post without saving")
    parser.add_argument("--topic", default="",
                        help="Custom topic to write about (bypasses news fetching)")
    parser.add_argument("--cve", action="store_true",
                        help="Generate a threat intel post from live CVE data (bypasses news fetching)")
    parser.add_argument("--knowledge", action="store_true",
                        help="Generate a thought leadership post from a private note in the knowledge/ folder")
    parser.add_argument("--limit", type=int, default=0,
                        help="Maximum number of posts to generate per day (0 for no limit)")
    args = parser.parse_args()

    # Step 0: Check daily limit
    if args.limit > 0:
        posts_dir = Path(__file__).parent.parent / "posts"
        today_prefix = args.date
        existing_posts = list(posts_dir.glob(f"{today_prefix}*.md"))
        if len(existing_posts) >= args.limit:
            print(f"[WARN] Daily post limit reached ({args.limit}). Existing posts today: {len(existing_posts)}.")
            print("[WARN] Aborting generation.")
            sys.exit(0)

    # Step 1: Determine topic vs news
    is_custom = False
    is_cve = False
    is_knowledge = False
    content_to_use = ""
    used_custom_file = False
    
    custom_idea_file = Path(__file__).parent.parent / "custom_idea.txt"

    if args.topic:
        is_custom = True
        content_to_use = args.topic
        print(f"[INFO] Using custom topic from command line: {args.topic}")
    elif args.cve:
        is_cve = True
        print("[INFO] Using Live Incident Response Tracker (--cve flag)")
        content_to_use = get_cve_context()
    elif args.knowledge:
        print("[INFO] Using Personal Brain / Knowledge Base (--knowledge flag)")
        knowledge_result = fetch_random_knowledge()
        if knowledge_result:
            content_to_use, filename = knowledge_result
            is_knowledge = True
            print(f"[INFO] Successfully loaded knowledge source: {filename}")
        else:
            print("[WARN] Could not load knowledge. Falling back to news.")
            content_to_use = get_news_context()
    elif custom_idea_file.exists():
        file_content = custom_idea_file.read_text(encoding="utf-8").strip()
        if file_content:
            is_custom = True
            content_to_use = file_content
            used_custom_file = True
            print(f"[INFO] Using custom topic from custom_idea.txt")
        else:
            print("[INFO] custom_idea.txt is empty. Falling back to news.")
            content_to_use = get_news_context()
    else:
        print("[INFO] Fetching daily news...")
        content_to_use = get_news_context()

    # Step 2: Generate post
    print(f"\n[INFO] Generating {get_style_for_display()} post...")
    raw_post_text = generate_post(content_to_use, is_custom=is_custom, is_cve=is_cve, is_knowledge=is_knowledge)
    
    # Step 2.5: Sense Check & Image Prompt
    final_post_text = verify_post(raw_post_text)
    image_prompt = generate_image_prompt(final_post_text)

    # Step 2.6: Log to history (extracting the main topic/link)
    try:
        # Extract title (first line) and first link found
        title_line = final_post_text.split("\n")[0][:100]
        links = re.findall(r'http\S+', final_post_text)
        first_link = links[0] if links else ""
        add_to_history(title_line, first_link)
        print(f"[INFO] Topic logged to history for anti-repetition.")
    except Exception as e:
        print(f"[WARN] Failed to log to history: {e}")

    # Step 2.7: Generate Canva-style image
    image_path = ""
    try:
        image_path = generate_post_image(final_post_text)
        print(f"[SUCCESS] Professional image generated: {image_path}")
    except Exception as e:
        print(f"[WARN] Image generation failed ({e}). Posting without image.")

    if args.dry_run:
        print("\n=== GENERATED POST ===\n")
        print(final_post_text)
        print("\n=== IMAGE ===\n")
        print(f"Image saved at: {image_path}")
        return

    # Clean up the custom idea file if we successfully used it (so it doesn't repeat tomorrow)
    if used_custom_file and not args.dry_run:
        try:
            custom_idea_file.unlink()
            print("[INFO] Deleted custom_idea.txt after successful generation.")
        except Exception as e:
            print(f"[WARN] Could not delete custom_idea.txt: {e}")

    # Step 3: Save post
    filepath = save_post(final_post_text, image_prompt, args.date, image_path)

    # Step 4: Output for GitHub Actions
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"post_file={filepath}\n")
            f.write(f"image_path={image_path}\n")
            f.write(f"post_text<<EOF\n{final_post_text}\nEOF\n")

    print("\n[SUCCESS] Post generation complete!")


if __name__ == "__main__":
    main()
