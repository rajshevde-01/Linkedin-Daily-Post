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

from config import GEMINI_API_KEY, get_system_prompt, HASHTAGS, POST_MIN_WORDS, POST_MAX_WORDS
from fetch_news import get_news_context


def generate_post(content: str, is_custom: bool = False) -> str:
    """Generate a LinkedIn post using Google Gemini API."""
    try:
        from google import genai
    except ImportError:
        print("[ERROR] google-genai package not installed. Run: pip install google-genai")
        sys.exit(1)

    if not GEMINI_API_KEY:
        print("[ERROR] GEMINI_API_KEY environment variable not set")
        sys.exit(1)

    client = genai.Client(api_key=GEMINI_API_KEY)

    system_prompt = get_system_prompt(content, is_custom=is_custom)

    # Added robust retry logic for 429 Rate Limits
    import time
    from google.genai import errors
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-pro",
                contents=system_prompt,
            )
            post_text = response.text.strip()
            break
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "Too Many Requests" in err_msg or "quota" in err_msg.lower():
                if attempt < max_retries - 1:
                    print(f"[WARN] Gemini API rate limit hit. Waiting 60s before retry {attempt+1}/{max_retries}...")
                    time.sleep(60)
                    continue
            print(f"[ERROR] Gemini API failed: {e}")
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

    filepath = posts_dir / f"{date_str}.md"

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
    args = parser.parse_args()

    # Step 1: Determine topic vs news
    is_custom = False
    content_to_use = ""
    used_custom_file = False
    
    custom_idea_file = Path(__file__).parent.parent / "custom_idea.txt"

    if args.topic:
        is_custom = True
        content_to_use = args.topic
        print(f"[INFO] Using custom topic from command line: {args.topic}")
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
    post_text = generate_post(content_to_use, is_custom=is_custom)

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
