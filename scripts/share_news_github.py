import os
import sys
import base64
import requests
import argparse
from datetime import datetime

# Add scripts directory to path to allow imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fetch_news import get_raw_articles, format_news_context


def post_news_to_github_issue(news_content: str, date_str: str) -> bool:
    """Creates a GitHub Issue containing the latest news digest."""
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")

    if not token or not repo:
        print("[ERROR] GITHUB_TOKEN or GITHUB_REPOSITORY environment variables not set.")
        return False

    url = f"https://api.github.com/repos/{repo}/issues"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    payload = {
        "title": f"🚨 Cybersecurity News Digest - {date_str}",
        "body": f"# 📰 Daily Cybersecurity News Digest\n*Generated on {date_str}*\n\n{news_content}",
        "labels": ["news-digest", "automated"],
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 201:
        issue_url = response.json().get("html_url")
        print(f"[SUCCESS] News shared via GitHub Issue: {issue_url}")
        return True
    else:
        print(f"[ERROR] Failed to create issue: {response.status_code}")
        print(response.text)
        return False


def commit_news_file_to_github(news_content: str, date_str: str) -> bool:
    """Commits a markdown file containing the news digest directly to the repo."""
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")

    if not token or not repo:
        print("[ERROR] GITHUB_TOKEN or GITHUB_REPOSITORY environment variables not set.")
        return False

    path = f"news/{date_str}-news.md"
    url = f"https://api.github.com/repos/{repo}/contents/{path}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    file_content = f"# 📰 Cybersecurity News Digest - {date_str}\n\n{news_content}"
    content_bytes = file_content.encode("utf-8")
    content_b64 = base64.b64encode(content_bytes).decode("utf-8")

    payload = {
        "message": f"docs: add news digest for {date_str}",
        "content": content_b64,
        "branch": "main",
    }

    # Check if the file already exists to get its SHA (required for updating)
    get_resp = requests.get(url, headers=headers)
    if get_resp.status_code == 200:
        payload["sha"] = get_resp.json().get("sha")

    response = requests.put(url, headers=headers, json=payload)

    if response.status_code in [200, 201]:
        file_url = response.json().get("content", {}).get("html_url")
        print(f"[SUCCESS] News file committed to GitHub: {file_url}")
        return True
    else:
        print(f"[ERROR] Failed to commit news file: {response.status_code}")
        print(response.text)
        return False


def main():
    parser = argparse.ArgumentParser(description="Share fetched news on GitHub")
    parser.add_argument(
        "--method",
        choices=["issue", "commit", "both"],
        default="both",
        help="Sharing method: 'issue' (creates issue), 'commit' (commits file), or 'both'",
    )
    args = parser.parse_args()

    date_str = datetime.now().strftime("%Y-%m-%d")
    print("[INFO] Fetching latest cybersecurity news...")

    articles = get_raw_articles()
    if not articles:
        print("[INFO] No news articles fetched today.")
        return

    news_content = format_news_context(articles)

    if args.method in ["issue", "both"]:
        post_news_to_github_issue(news_content, date_str)

    if args.method in ["commit", "both"]:
        commit_news_file_to_github(news_content, date_str)


if __name__ == "__main__":
    main()
