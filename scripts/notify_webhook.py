import os
import argparse
import requests
import json
from pathlib import Path

def parse_post_file(filepath):
    """Parse frontmatter and content from post markdown file."""
    path = Path(filepath)
    if not path.exists():
        print(f"[ERROR] file {filepath} not found.")
        return None, ""
        
    content = path.read_text(encoding="utf-8")
    # Simple frontmatter split
    parts = content.split("---")
    if len(parts) >= 3:
        # parts[1] is frontmatter, parts[2:] is content
        body = "---".join(parts[2:]).strip()
        metadata = {}
        for line in parts[1].split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                metadata[k.strip()] = v.strip()
        return metadata, body
        
    return {}, content

def send_webhook(message, webhook_url):
    """Send message to webhook with proper JSON layout mapping."""
    if not webhook_url:
        print("[WARN] No webhook URL provided. Skipping.")
        return False

    is_discord = "discord.com" in webhook_url
    
    if is_discord:
        # Discord expects 'content'
        payload = {"content": message}
    else:
        # Slack / standard expects 'text'
        payload = {"text": message}

    try:
        response = requests.post(
            webhook_url, 
            json=payload, 
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        if response.status_code < 300:
            print("[SUCCESS] Webhook notification sent.")
            return True
        else:
            print(f"[ERROR] Webhook failed with {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"[ERROR] Webhook exception: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Send Live Post Preview to Slack/Discord")
    parser.add_argument("--file", help="Path to markdown post file")
    parser.add_argument("--message", help="Custom message to send instead of file contents")
    args = parser.parse_args()

    webhook_url = os.environ.get("SLACK_WEBHOOK_URL") or os.environ.get("DISCORD_WEBHOOK_URL")

    if args.message:
        send_webhook(args.message, webhook_url)
        return

    if not args.file:
        print("[ERROR] Must provide either --file or --message")
        return

    metadata, body = parse_post_file(args.file)
    style = metadata.get("style", "Standard")
    date_str = metadata.get("date", "Today")
    word_count = metadata.get("word_count", "0")

    # Format a beautiful notification block
    formatted_msg = f"""🚨 **[DAILY POST QUEUED]** 🚨
📅 **Date**: {date_str}
🎭 **Style**: {style}
📊 **Metric**: {word_count} words

---
{body[:500]}... *(Read full on LinkedIn or Git)*
---
"""

    send_webhook(formatted_msg, webhook_url)

if __name__ == "__main__":
    main()
