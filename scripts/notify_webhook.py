"""
Send post preview or status alerts to Slack / Discord webhooks.
V2: Added --status flag for success/failure colored notifications.
"""
import os
import argparse
import requests
from datetime import datetime
from pathlib import Path


def parse_post_file(filepath):
    """Parse frontmatter and content from post markdown file."""
    path = Path(filepath)
    if not path.exists():
        print(f"[ERROR] file {filepath} not found.")
        return {}, ""

    content = path.read_text(encoding="utf-8")
    parts = content.split("---")
    if len(parts) >= 3:
        body = "---".join(parts[2:]).strip()
        metadata = {}
        for line in parts[1].split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                metadata[k.strip()] = v.strip()
        return metadata, body

    return {}, content


def _post(webhook_url: str, payload: dict) -> bool:
    """Internal helper — POST a JSON payload to a webhook URL."""
    if not webhook_url:
        print("[WARN] No webhook URL set. Skipping.")
        return False
    try:
        resp = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        if resp.status_code < 300:
            print("[SUCCESS] Webhook notification sent.")
            return True
        else:
            print(f"[ERROR] Webhook returned {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        print(f"[ERROR] Webhook exception: {e}")
        return False


def send_webhook(message: str, webhook_url: str) -> bool:
    """Send a plain-text message to Discord or Slack."""
    is_discord = "discord.com" in (webhook_url or "")
    payload = {"content": message} if is_discord else {"text": message}
    return _post(webhook_url, payload)


def notify_failure(error_message: str, webhook_url: str):
    """Send a red ❌ failure alert when LinkedIn posting fails."""
    if not webhook_url:
        print("[WARN] No webhook URL set. Cannot send failure alert.")
        return

    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    is_discord = "discord.com" in webhook_url

    if is_discord:
        embed = {
            "title": "❌ LinkedIn Post FAILED",
            "description": f"```\n{error_message[:1000]}\n```",
            "color": 0xE74C3C,   # red
            "footer": {"text": f"LinkedIn Automation • {timestamp}"},
        }
        ok = _post(webhook_url, {"embeds": [embed]})
    else:
        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": "❌ LinkedIn Post FAILED", "emoji": True}},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Error:*\n```{error_message[:900]}```"}},
            {"type": "context", "elements": [{"type": "mrkdwn", "text": f"LinkedIn Automation • {timestamp}"}]},
        ]
        ok = _post(webhook_url, {"blocks": blocks})

    if not ok:
        send_webhook(f"❌ LinkedIn Post FAILED\n{error_message[:500]}", webhook_url)


def notify_success(metadata: dict, body: str, webhook_url: str):
    """Send a green 🚨 queued post preview."""
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    style = metadata.get("style", "Standard")
    date_str = metadata.get("date", "Today")
    word_count = metadata.get("word_count", "0")
    preview = (body[:480] + "...") if len(body) > 480 else body
    is_discord = "discord.com" in (webhook_url or "")

    if is_discord:
        embed = {
            "title": "🚨 Daily Post Queued",
            "description": f"**Date**: {date_str}\n**Style**: {style}\n**Words**: {word_count}\n\n{preview}",
            "color": 0x2ECC71,   # green
            "footer": {"text": f"LinkedIn Automation • {timestamp}"},
        }
        ok = _post(webhook_url, {"embeds": [embed]})
    else:
        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": "🚨 Daily Post Queued", "emoji": True}},
            {"type": "section", "fields": [
                {"type": "mrkdwn", "text": f"*Date:* {date_str}"},
                {"type": "mrkdwn", "text": f"*Style:* {style}"},
                {"type": "mrkdwn", "text": f"*Words:* {word_count}"},
            ]},
            {"type": "section", "text": {"type": "mrkdwn", "text": preview}},
            {"type": "context", "elements": [{"type": "mrkdwn", "text": f"LinkedIn Automation • {timestamp}"}]},
        ]
        ok = _post(webhook_url, {"blocks": blocks})

    if not ok:
        fallback = (
            f"🚨 **[DAILY POST QUEUED]** 🚨\n"
            f"📅 **Date**: {date_str}\n🎭 **Style**: {style}\n📊 **Words**: {word_count}\n\n---\n{preview}\n---"
        )
        send_webhook(fallback, webhook_url)


def main():
    parser = argparse.ArgumentParser(description="Send post preview or status alert to Slack/Discord")
    parser.add_argument("--file", help="Path to markdown post file")
    parser.add_argument("--message", help="Custom message to send")
    parser.add_argument(
        "--status",
        choices=["success", "failure"],
        default="success",
        help="Notification type: 'success' (post preview) or 'failure' (error alert)",
    )
    args = parser.parse_args()

    webhook_url = os.environ.get("SLACK_WEBHOOK_URL") or os.environ.get("DISCORD_WEBHOOK_URL")

    if not webhook_url:
        print("[WARN] Neither SLACK_WEBHOOK_URL nor DISCORD_WEBHOOK_URL is set. Skipping.")
        return

    if args.status == "failure":
        error_msg = args.message or "An unspecified error occurred during LinkedIn posting."
        notify_failure(error_msg, webhook_url)
        return

    if args.message:
        send_webhook(args.message, webhook_url)
        return

    if not args.file:
        print("[ERROR] Must provide --file, --message, or --status failure")
        return

    metadata, body = parse_post_file(args.file)
    notify_success(metadata, body, webhook_url)


if __name__ == "__main__":
    main()
