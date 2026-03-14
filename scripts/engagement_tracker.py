import os
import sys
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path

# Add scripts dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import LINKEDIN_ACCESS_TOKEN
from history import load_history, save_history

def fetch_linkedin_metrics(post_id):
    """Fetch likes and comments count for a specific post URN."""
    if not LINKEDIN_ACCESS_TOKEN:
        print("[ERROR] LINKEDIN_ACCESS_TOKEN not set")
        return None

    # Handle numeric IDs or URNs
    urn = post_id
    if not urn.startswith("urn:li:"):
        urn = f"urn:li:share:{post_id}"

    # LinkedIn Community Management API: socialActions endpoint
    # Note: Requires specific 'Community Management' scopes
    url = f"https://api.linkedin.com/rest/socialActions/{urn}"
    
    headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "LinkedIn-Version": "202601",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            # The response usually contains totalShareStatistics or similar summary
            # We'll try to extract common fields
            likes = data.get("totalShareStatistics", {}).get("likeCount", 0)
            comments = data.get("totalShareStatistics", {}).get("commentCount", 0)
            return {"likes": likes, "comments": comments}
        else:
            print(f"[WARN] Failed to fetch metrics for {urn}: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"[ERROR] Exception while fetching metrics: {e}")
        return None

def update_all_metrics():
    """Iterate through history and update metrics for recently posted items."""
    history = load_history()
    if not history.get("posts"):
        print("[INFO] No posts found in history to track.")
        return

    updated_count = 0
    # Only track posts from the last 7 days to avoid excessive API calls
    cutoff_date = datetime.now() - timedelta(days=7)

    for post in history["posts"]:
        posted_at = datetime.strptime(post["posted_at"], "%Y-%m-%d %H:%M:%S")
        if posted_at > cutoff_date:
            print(f"[INFO] Tracking post: {post['id']} ({post['title']})")
            metrics = fetch_linkedin_metrics(post["id"])
            if metrics:
                post["metrics"] = metrics
                updated_count += 1

    if updated_count > 0:
        save_history(history)
        print(f"[SUCCESS] Updated metrics for {updated_count} posts.")
    else:
        print("[INFO] No metrics were updated.")

if __name__ == "__main__":
    update_all_metrics()
