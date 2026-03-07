"""
Post to LinkedIn using the LinkedIn Community Management API.
Also handles confirmation status checking.
"""
import os
import sys
import json
import argparse
import requests
import re
from datetime import datetime
from pathlib import Path

# Add scripts dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import LINKEDIN_ACCESS_TOKEN, LINKEDIN_PERSON_URN, HASHTAGS


def clean_markdown_for_linkedin(text: str) -> str:
    """
    Remove markdown artifacts (bold, italic, links, headers) to ensure 
    clean plain text rendering on LinkedIn.
    """
    if not text:
        return text

    # Remove bold (**text** or __text__)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    
    # Remove italic (*text* or _text_)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    
    # Convert links [Title](URL) -> Title: URL
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'\1: \2', text)
    
    # Remove headers (### Text -> Text)
    text = re.sub(r'^#+\s+(.*?)$', r'\1', text, flags=re.MULTILINE)
    
    # Remove stray backticks that might have been used for inline quotes
    text = text.replace('`', '')
    
    return text.strip()


def post_to_linkedin(text: str) -> dict:
    """Publish a text post to LinkedIn using the REST Posts API."""
    if not LINKEDIN_ACCESS_TOKEN:
        print("[ERROR] LINKEDIN_ACCESS_TOKEN not set")
        sys.exit(1)

    if not LINKEDIN_PERSON_URN:
        print("[ERROR] LINKEDIN_PERSON_URN not set (e.g., 'urn:li:person:XXXXXXXX')")
        sys.exit(1)

    url = "https://api.linkedin.com/rest/posts"

    # Clean the markdown from the text before sending to LinkedIn
    cleaned_text = clean_markdown_for_linkedin(text)

    headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "LinkedIn-Version": "202601",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    payload = {
        "author": LINKEDIN_PERSON_URN,
        "commentary": cleaned_text,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 201:
        post_id = response.headers.get("x-restli-id", "unknown")
        print(f"[SUCCESS] Post published to LinkedIn! (ID: {post_id})")
        return {"id": post_id}
    else:
        print(f"[ERROR] LinkedIn API returned {response.status_code}")
        print(f"[ERROR] Response: {response.text}")
        sys.exit(1)


def read_post_file(date_str: str) -> tuple[str, dict]:
    """Read the generated post file and return (text, metadata)."""
    posts_dir = Path(__file__).parent.parent / "posts"
    filepath = posts_dir / f"{date_str}.md"

    if not filepath.exists():
        print(f"[ERROR] Post file not found: {filepath}")
        sys.exit(1)

    content = filepath.read_text(encoding="utf-8")

    # Parse YAML frontmatter
    parts = content.split("---")
    metadata = {}
    post_text = content

    if len(parts) >= 3:
        import yaml
        try:
            metadata = yaml.safe_load(parts[1]) or {}
        except Exception:
            pass
        post_text = "---".join(parts[2:]).strip()

    return post_text, metadata


def update_post_status(date_str: str, new_status: str):
    """Update the status in the post's YAML frontmatter."""
    posts_dir = Path(__file__).parent.parent / "posts"
    filepath = posts_dir / f"{date_str}.md"

    if not filepath.exists():
        return

    content = filepath.read_text(encoding="utf-8")
    # Simple replacement
    content = content.replace("status: pending", f"status: {new_status}")
    content = content.replace("status: confirmed", f"status: {new_status}")
    filepath.write_text(content, encoding="utf-8")
    print(f"[INFO] Updated post status to: {new_status}")


def check_confirmation_status(date_str: str) -> str:
    """
    Check if the user has confirmed/rejected the post.
    Checks the post file's status field.
    Returns: 'pending', 'confirmed', 'rejected', or 'not_found'
    """
    posts_dir = Path(__file__).parent.parent / "posts"
    filepath = posts_dir / f"{date_str}.md"

    if not filepath.exists():
        return "not_found"

    content = filepath.read_text(encoding="utf-8")

    if "status: rejected" in content:
        return "rejected"
    elif "status: confirmed" in content:
        return "confirmed"
    elif "status: posted" in content:
        return "posted"
    else:
        return "pending"


def main():
    parser = argparse.ArgumentParser(description="Post to LinkedIn")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"),
                        help="Date of the post to publish (YYYY-MM-DD)")
    parser.add_argument("--check-status", action="store_true",
                        help="Just check confirmation status, don't post")
    parser.add_argument("--force", action="store_true",
                        help="Post even if status is pending (auto-post after timeout)")
    args = parser.parse_args()

    if args.check_status:
        status = check_confirmation_status(args.date)
        print(f"[INFO] Post status for {args.date}: {status}")
        # Output for GitHub Actions
        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output:
            with open(github_output, "a") as f:
                f.write(f"status={status}\n")
        return

    # Find all posts for the given date
    posts_dir = Path(__file__).parent.parent / "posts"
    post_files = sorted(list(posts_dir.glob(f"{args.date}-*.md")))
    if not post_files:
        post_files = [posts_dir / f"{args.date}.md"] if (posts_dir / f"{args.date}.md").exists() else []

    if not post_files:
        print(f"[INFO] No post files found for {args.date}.")
        return

    for filepath in post_files:
        filename = filepath.stem
        # check_confirmation_status string-matches the date_str
        status = check_confirmation_status(filename)

        if status == "posted":
            print(f"[INFO] Post {filename} already published. Skipping.")
            continue

        if status == "rejected":
            print(f"[INFO] Post {filename} was rejected by user. Skipping.")
            continue

        if status == "pending" and not args.force:
            print(f"[INFO] Post {filename} is pending confirmation. Use --force to post anyway.")
            continue

        # Read the post
        post_text, metadata = read_post_file(filename)

        # Post to LinkedIn
        print(f"[INFO] Publishing post {filename} to LinkedIn...")
        result = post_to_linkedin(post_text)

        # Update status
        update_post_status(filename, "posted")

    print("[SUCCESS] Done!")


if __name__ == "__main__":
    main()
