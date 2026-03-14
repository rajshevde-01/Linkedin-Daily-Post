import json
import os
from pathlib import Path
from datetime import datetime

HISTORY_FILE = Path(__file__).parent.parent / "history.json"

def load_history():
    """Load the history of used titles, links, and posts."""
    default = {"titles": [], "links": [], "posts": [], "last_updated": ""}
    if not HISTORY_FILE.exists():
        return default
    try:
        with open(HISTORY_FILE, "r") as f:
            data = json.load(f)
            # Ensure the structure is correct
            if not isinstance(data.get("titles"), list): data["titles"] = []
            if not isinstance(data.get("links"), list): data["links"] = []
            if not isinstance(data.get("posts"), list): data["posts"] = []
            return data
    except Exception:
        return default

def save_history(history):
    """Save the history to file (keeping only the last 50 entries)."""
    history["titles"] = history["titles"][-50:]
    history["links"] = history["links"][-50:]
    history["posts"] = history["posts"][-50:]
    history["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

def is_in_history(title, link):
    """Check if a title or link was recently used."""
    history = load_history()
    # Normalize title for comparison
    norm_title = title.lower().strip()
    
    # Check for direct link match
    if link in history["links"]:
        return True
    
    # Check for similar title match
    for h_title in history["titles"]:
        if norm_title in h_title or h_title in norm_title:
             return True
             
    return False

def add_to_history(title, link):
    """Add a new entry to the history (legacy list support)."""
    history = load_history()
    history["titles"].append(title.lower().strip())
    history["links"].append(link)
    save_history(history)

def add_post_to_history(post_id, title, link, content):
    """Add a full post entry to history for tracking."""
    history = load_history()
    entry = {
        "id": post_id,
        "title": title.lower().strip(),
        "link": link,
        "content_preview": content[:200], # Keep a bit of content for prompt injection
        "posted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "metrics": {"likes": 0, "comments": 0}
    }
    history["posts"].append(entry)
    
    # Also update legacy lists for duplication check
    history["titles"].append(entry["title"])
    history["links"].append(link)
    
    save_history(history)
