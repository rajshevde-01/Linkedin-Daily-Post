import requests
import os
import sys
from typing import Optional, Dict

def fetch_top_github_repo(topic: str) -> Optional[Dict]:
    """Search GitHub for top-starred repo matching a topic, specifically security tools."""
    # Enhance the search query for tech repositories
    query = f"{topic} security tool"
    url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page=1"
    
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "LinkedIn-Automation-Bot"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("total_count", 0) > 0:
                item = data["items"][0]
                return {
                    "name": item["full_name"],
                    "stars": item["stargazers_count"],
                    "description": item["description"][:160] + ("..." if len(item["description"] or "") > 160 else ""),
                    "url": item["html_url"]
                }
            else:
                print(f"[INFO] No GitHub repos found for {topic}")
                return None
        else:
            print(f"[WARN] GitHub API failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"[ERROR] GitHub search failed: {e}")
        return None

if __name__ == "__main__":
    test_topic = sys.argv[1] if len(sys.argv) > 1 else "Zero Trust"
    print(f"[INFO] Testing GitHub fetch for: {test_topic}")
    repo = fetch_top_github_repo(test_topic)
    if repo:
        print(f"[SUCCESS] Top Repo: {repo['name']} (⭐ {repo['stars']})")
        print(f"         {repo['description']}")
        print(f"         Link: {repo['url']}")
