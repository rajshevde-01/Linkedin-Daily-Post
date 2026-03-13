import json
import os
from pathlib import Path
from datetime import datetime

HISTORY_FILE = Path(__file__).parent.parent / "history.json"

def load_history():
    """Load the history of used titles and links."""
    default = {"titles": [], "links": [], "last_updated": ""}
    if not HISTORY_FILE.exists():
        return default
    try:
        with open(HISTORY_FILE, "r") as f:
            data = json.load(f)
            # Ensure the structure is correct
            if not isinstance(data.get("titles"), list): data["titles"] = []
            if not isinstance(data.get("links"), list): data["links"] = []
            return data
    except Exception:
        return default

def save_history(history):
    """Save the history to file (keeping only the last 50 entries)."""
    history["titles"] = history["titles"][-50:]
    history["links"] = history["links"][-50:]
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
    """Add a new entry to the history."""
    history = load_history()
    history["titles"].append(title.lower().strip())
    history["links"].append(link)
    save_history(history)
