import os
import json
import re
from datetime import datetime
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).parent.parent
HISTORY_FILE = ROOT_DIR / "history.json"
README_FILE = ROOT_DIR / "README.md"

def load_history():
    if not HISTORY_FILE.exists():
        return {"posts": [], "titles": []}
    with open(HISTORY_FILE, "r") as f:
        return json.load(f)

def generate_stats_markdown(history):
    posts = history.get("posts", [])
    total_posts = len(posts)
    
    # Calculate stats
    total_likes = sum(p.get("metrics", {}).get("likes", 0) for p in posts)
    total_comments = sum(p.get("metrics", {}).get("comments", 0) for p in posts)
    
    # Simple streak calculation (mocked for now based on dates in history)
    # real streak would require checking consecutive dates
    streak = 0
    if posts:
        dates = sorted(list(set(p["posted_at"][:10] for p in posts)), reverse=True)
        today = datetime.now().strftime("%Y-%m-%d")
        last_date = dates[0]
        # if today == last_date or yesterday == last_date...
        streak = len(dates) # simple count of unique active days for now
        
    last_updated = datetime.now().strftime("%Y-%m-%d")
    
    # Top 3 Posts by engagement (likes + comments)
    top_posts = sorted(posts, key=lambda p: (p.get("metrics", {}).get("likes", 0) + p.get("metrics", {}).get("comments", 0)), reverse=True)[:3]
    
    lines = [
        "| Metric | Value |",
        "|--------|-------|",
        f"| 🗓️ Last Updated | {last_updated} |",
        f"| 📝 Total Posts | {total_posts} |",
        f"| 👍 Total Likes | {total_likes} |",
        f"| 💬 Total Comments | {total_comments} |",
        f"| 🔥 Active Days | {streak} |",
        "",
        "### 🏆 Top Performing Posts",
        "",
        "| Post | Engagement |",
        "|------|------------|",
    ]
    
    for p in top_posts:
        engagement = p.get("metrics", {}).get("likes", 0) + p.get("metrics", {}).get("comments", 0)
        title_preview = p.get("title", "Untitled")[:50].strip() + ("..." if len(p.get("title", "")) > 50 else "")
        # Remove markdown bolding from title if present for table cleanliness
        title_preview = title_preview.replace("**", "")
        lines.append(f"| {title_preview} | {engagement} |")
        
    return "\n".join(lines)

def update_readme():
    if not README_FILE.exists():
        print("[ERROR] README.md not found")
        return

    history = load_history()
    stats_md = generate_stats_markdown(history)
    
    with open(README_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Regex to find the stats block
    pattern = r"<!-- STATS_START -->.*?<!-- STATS_END -->"
    replacement = f"<!-- STATS_START -->\n{stats_md}\n<!-- STATS_END -->"
    
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    with open(README_FILE, "w", encoding="utf-8") as f:
        f.write(new_content)
    
    print("[SUCCESS] README.md dashboard updated!")

if __name__ == "__main__":
    update_readme()
