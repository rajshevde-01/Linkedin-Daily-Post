"""
Generate LinkedIn post using Google Gemini API.
"""
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

# Add scripts dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import GEMINI_API_KEYS, get_system_prompt, HASHTAGS, POST_MIN_WORDS, POST_MAX_WORDS
from fetch_news import get_news_context
from fetch_cve import get_cve_context

def generate_post(content: str, is_custom: bool = False, is_cve: bool = False) -> str:
    """Generate a LinkedIn post using Google Gemini API."""
    try:
        from google import genai
    except ImportError:
        print("[ERROR] google-genai package not installed. Run: pip install google-genai")
        sys.exit(1)

    if not GEMINI_API_KEYS:
        print("[ERROR] GEMINI_API_KEY environment variable not set or invalid")
        sys.exit(1)

    system_prompt = get_system_prompt(content, is_custom=is_custom, is_cve=is_cve)

    # Added robust retry and fallback logic for Rate Limits / Quotas
    import time
    
    max_retries = 3
    models_to_try = ["gemini-2.5-pro", "gemini-2.0-flash"]
    
    post_text = None
    last_error = None
    
    # Outer Loop: Try each model
    for current_model in models_to_try:
        if post_text is not None:
            break
            
        print(f"\n[INFO] Starting attempts with model {current_model}...")
        
        # Middle Loop: Try each API key for the current model
        for key_idx, api_key in enumerate(GEMINI_API_KEYS):
            if post_text is not None:
                break
                
            print(f"[INFO] Using API key #{key_idx + 1}/{len(GEMINI_API_KEYS)} for {current_model}...")
            client = genai.Client(api_key=api_key)
            
            # Inner Loop: Retries for temporary issues (like concurrent requests)
            for attempt in range(max_retries):
                try:
                    response = client.models.generate_content(
                        model=current_model,
                        contents=system_prompt,
                    )
                    post_text = response.text.strip()
                    print(f"[SUCCESS] Generation successful with {current_model} (Key #{key_idx + 1})")
                    break  # Success, break inner loop
                except Exception as e:
                    err_msg = str(e)
                    last_error = e
                    
                    if "429" in err_msg or "Too Many Requests" in err_msg or "quota" in err_msg.lower() or "400" in err_msg or "API_KEY_INVALID" in err_msg:
                        print(f"[WARN] Quota exhausted or invalid key for {current_model} using Key #{key_idx + 1}: {e}")
                        # Immediately fail this key and move to the next key without retrying wait times
                        # Quota exhaustion or invalid keys mean we shouldn't wait, but rather switch keys immediately.
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
        print(f"\n[FATAL] Exhausted all {len(models_to_try)} models across all {len(GEMINI_API_KEYS)} API keys.")
        print(f"[FATAL] Last error encountered: {last_error}")
        sys.exit(1)

    # Validate word count
    word_count = len(post_text.split())
    print(f"[INFO] Generated post: {word_count} words")

    if word_count < POST_MIN_WORDS or word_count > POST_MAX_WORDS:
        print(f"[WARN] Word count {word_count} outside target range ({POST_MIN_WORDS}-{POST_MAX_WORDS})")

    return post_text


def add_hashtags(post_text: str) -> str:
    """Append hashtags to the post."""
    return post_text + "\n\n" + " ".join(HASHTAGS)


def save_post(post_text: str, date_str: str, with_hashtags: bool = True) -> str:
    """Save post to posts/ directory and return the file path."""
    posts_dir = Path(__file__).parent.parent / "posts"
    posts_dir.mkdir(exist_ok=True)

    # To support multiple posts per day, append an index if necessary
    index = 1
    filepath = posts_dir / f"{date_str}-{index}.md"
    while filepath.exists():
        index += 1
        filepath = posts_dir / f"{date_str}-{index}.md"

    full_post = add_hashtags(post_text) if with_hashtags else post_text

    content = f"""---
date: {date_str}
status: pending
style: {get_style_for_display()}
word_count: {len(post_text.split())}
generated_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
---

{full_post}
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
    post_text = generate_post(content_to_use, is_custom=is_custom, is_cve=is_cve)

    if args.dry_run:
        print("\n=== GENERATED POST ===\n")
        print(post_text)
        print(f"\n=== WITH HASHTAGS ===\n")
        print(add_hashtags(post_text))
        return

    # Clean up the custom idea file if we successfully used it (so it doesn't repeat tomorrow)
    if used_custom_file and not args.dry_run:
        try:
            custom_idea_file.unlink()
            print("[INFO] Deleted custom_idea.txt after successful generation.")
        except Exception as e:
            print(f"[WARN] Could not delete custom_idea.txt: {e}")

    # Step 3: Save post
    filepath = save_post(post_text, args.date)

    # Step 4: Output for GitHub Actions
    # Write to GITHUB_OUTPUT if available
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"post_file={filepath}\n")
            # Use delimiter for multiline output
            f.write(f"post_text<<EOF\n{post_text}\nEOF\n")
            f.write(f"post_with_hashtags<<EOF\n{add_hashtags(post_text)}\nEOF\n")

    print("\n[SUCCESS] Post generation complete!")


if __name__ == "__main__":
    main()
