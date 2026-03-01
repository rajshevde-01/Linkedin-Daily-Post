"""
Send confirmation notification via GitHub Issues.
Creates an issue with the post content for user review.
User can comment 'approve' or 'reject' on the issue, or do nothing (auto-posts after timeout).
"""
import os
import sys
import json
import argparse
import requests
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def create_github_issue(post_text: str, date_str: str, style: str) -> int:
    """Create a GitHub Issue with the post for review."""
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")

    if not token or not repo:
        print("[ERROR] GITHUB_TOKEN or GITHUB_REPOSITORY not available")
        return -1

    url = f"https://api.github.com/repos/{repo}/issues"

    body = f"""## LinkedIn Post for {date_str}
**Style:** {style}
**Auto-posts at:** 11:11 PM IST (if no response)

---

{post_text}

---

### How to respond:
- **Approve**: Comment `approve` or close this issue — the post will go live at 11:11 PM IST
- **Reject**: Comment `reject` — the post will NOT be published
- **No response**: Post will be automatically published at 11:11 PM IST

> You have 3 hours to review. If you don't respond, the post goes live automatically.
"""

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    payload = {
        "title": f"[LinkedIn Post] {date_str} - {style}",
        "body": body,
        "labels": ["linkedin-post", "pending-review"],
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 201:
        issue_num = response.json()["number"]
        print(f"[SUCCESS] Created GitHub Issue #{issue_num} for review")
        return issue_num
    else:
        print(f"[ERROR] Failed to create issue: {response.status_code}")
        print(f"[ERROR] {response.text}")
        return -1


def check_issue_response(date_str: str) -> str:
    """
    Check if the user responded to the confirmation issue.
    Returns: 'approved', 'rejected', or 'no_response'
    """
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")

    if not token or not repo:
        return "no_response"

    # Search for today's issue
    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    params = {
        "labels": "linkedin-post,pending-review",
        "state": "all",
        "sort": "created",
        "direction": "desc",
        "per_page": 5,
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        print(f"[WARN] Failed to fetch issues: {response.status_code}")
        return "no_response"

    issues = response.json()

    # Find today's issue
    target_issue = None
    for issue in issues:
        if date_str in issue.get("title", ""):
            target_issue = issue
            break

    if not target_issue:
        print(f"[WARN] No issue found for date {date_str}")
        return "no_response"

    issue_number = target_issue["number"]

    # Check if issue is closed (= approved)
    if target_issue["state"] == "closed":
        return "approved"

    # Check comments for approve/reject
    comments_url = target_issue["comments_url"]
    comments_response = requests.get(comments_url, headers=headers)

    if comments_response.status_code == 200:
        comments = comments_response.json()
        for comment in comments:
            body = comment.get("body", "").strip().lower()
            if "reject" in body:
                close_issue(issue_number, token, repo)
                return "rejected"
            elif "approve" in body:
                close_issue(issue_number, token, repo)
                return "approved"

    return "no_response"


def close_issue(issue_number: int, token: str, repo: str):
    """Close a GitHub issue."""
    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    requests.patch(url, headers=headers, json={"state": "closed"})


def main():
    parser = argparse.ArgumentParser(description="Send/check post confirmation")
    parser.add_argument("--action", required=True, choices=["notify", "check"],
                        help="'notify' to create issue, 'check' to check response")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--post-text", default="", help="Post text (for notify action)")
    parser.add_argument("--style", default="", help="Post style (for notify action)")
    args = parser.parse_args()

    if args.action == "notify":
        post_text = args.post_text
        if not post_text:
            # Read from post file
            posts_dir = Path(__file__).parent.parent / "posts"
            matching_files = sorted(list(posts_dir.glob(f"{args.date}*.md")))
            
            if matching_files:
                post_file = matching_files[-1]  # Get the latest one
                content = post_file.read_text(encoding="utf-8")
                parts = content.split("---")
                if len(parts) >= 3:
                    post_text = "---".join(parts[2:]).strip()

        if not post_text:
            print("[ERROR] No post text provided or found")
            sys.exit(1)

        create_github_issue(post_text, args.date, args.style or "Daily Post")

    elif args.action == "check":
        result = check_issue_response(args.date)
        print(f"[INFO] Confirmation status: {result}")

        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output:
            with open(github_output, "a") as f:
                f.write(f"confirmation={result}\n")


if __name__ == "__main__":
    main()
