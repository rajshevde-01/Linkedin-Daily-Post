import json
import os
import re
from pathlib import Path
from typing import List, Dict, Any

# Paths
ROOT_DIR = Path(__file__).parent.parent
MEMORY_FILE = ROOT_DIR / "memory.json"

def load_memory() -> List[Dict[str, Any]]:
    """Load the semantic memory store."""
    if not MEMORY_FILE.exists():
        return []
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_memory(memory: List[Dict[str, Any]]):
    """Save the semantic memory store."""
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2)

def extract_keywords(text: str) -> List[str]:
    """Basic keyword extraction (fallback if LLM doesn't provide them)."""
    # Remove special chars and lowercase
    clean = re.sub(r"[^a-zA-Z0-9\s]", "", text).lower()
    words = clean.split()
    # Filter out common stop words / noise
    stop_words = {"the", "and", "that", "this", "with", "from", "your", "their", "about", "could", "would", "cybersecurity", "security"}
    keywords = [w for w in words if len(w) > 3 and w not in stop_words]
    return list(set(keywords))

def add_to_memory(post_id: str, title: str, keywords: List[str]):
    """Add a new post record with its semantic keywords."""
    memory = load_memory()
    
    # Check if already exists
    if any(m["id"] == post_id for m in memory):
        return

    entry = {
        "id": post_id,
        "title": title,
        "keywords": [k.lower() for k in keywords if k],
        "created_at": os.environ.get("CURRENT_DATE", "") # Mocked or passed
    }
    
    memory.append(entry)
    # Keep only last 100 posts to maintain speed
    save_memory(memory[-100:])

def search_memory(query_keywords: List[str], top_k: int = 3) -> List[Dict[str, Any]]:
    """Find past posts with the high keyword overlap."""
    memory = load_memory()
    if not memory:
        return []

    target = set(k.lower() for k in query_keywords)
    results = []

    for entry in memory:
        entry_keywords = set(entry["keywords"])
        overlap = len(target.intersection(entry_keywords))
        if overlap > 0:
            results.append({
                "id": entry["id"],
                "title": entry["title"],
                "overlap": overlap,
                "score": overlap / max(len(target), 1)
            })

    # Sort by overlap score
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]

if __name__ == "__main__":
    # Test
    add_to_memory("test-1", "Zero Trust in the Age of Ransomware", ["Zero Trust", "Ransomware", "Identity", "Architecture"])
    add_to_memory("test-2", "Supply Chain Security and SolarWinds", ["Supply Chain", "SolarWinds", "Vulnerability", "Security"])
    
    print("[INFO] Searching memory for 'Ransomware Zero Trust'...")
    matches = search_memory(["Ransomware", "Zero", "Trust"])
    for m in matches:
        print(f"- Match: {m['title']} (Score: {m['score']:.2f})")
